"""
Event Analyzer — el cerebro que le da SENTIDO a un evento.

Toma un evento crudo del Event Engine y responde:
  ¿por qué pasa? · ¿qué impacto tiene? · ¿qué debería hacer?
Calcula un score de prioridad (impacto + urgencia + probabilidad), ajusta la
severidad (una prenda que se agota YA es 🔴 aunque "stock bajo" naciera 🟡) y
propone una acción PREPARABLE (que el Jefe confirma; nunca se ejecuta sola).
"""
import math
from datetime import date, timedelta

from sqlalchemy import func

from app import db
from app.models import Factura, FacturaDetalle, Evento, PrecioColegio


def _costo_estimado(cid, pid, unidades):
    """Costo aproximado de reponer `unidades` (usa el costo registrado, si hay)."""
    if not (cid and pid and unidades):
        return None
    row = (PrecioColegio.query
           .filter_by(id_colegio=cid, id_producto=pid)
           .filter(PrecioColegio.costo_unitario.isnot(None)).first())
    return round(row.costo_unitario * unidades) if row and row.costo_unitario else None

# El proveedor tarda ~7 días en reponer (regla de negocio; ajustable).
LEAD_TIME_DIAS = 7
VENTANA_VENTAS = 7          # días para medir el ritmo de ventas
COBERTURA_OBJETIVO = LEAD_TIME_DIAS + 7   # apuntar a ~2 semanas de stock
UMBRAL_REAL_BAJO = 3        # sin ventas, solo preocupa si el stock es <= esto

_SCORE_POR_SEV = {'CRITICO': 85, 'IMPORTANTE': 60, 'PRECAUCION': 40, 'INFORMATIVO': 20}


def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def priority_score(impacto, urgencia, probabilidad):
    """Puntaje 0-100. La urgencia pesa más que el impacto; la probabilidad
    modula. Permite ordenar y decidir qué SÍ se notifica."""
    return int(round(_clamp(0.40 * impacto + 0.45 * urgencia + 0.15 * probabilidad)))


def _sev_por_score(score, minimo='PRECAUCION'):
    orden = ['PRECAUCION', 'IMPORTANTE', 'CRITICO']
    calc = 'CRITICO' if score >= 80 else 'IMPORTANTE' if score >= 55 else 'PRECAUCION'
    # nunca por debajo del mínimo pedido
    return calc if orden.index(calc) >= orden.index(minimo) else minimo


def velocidad_ventas(dias=VENTANA_VENTAS):
    """Unidades vendidas por (colegio, producto, talla) en la ventana. Excluye
    facturas anuladas. Devuelve dict {(cid, pid, talla): unidades}."""
    corte = date.today() - timedelta(days=dias)
    filas = (db.session.query(
                Factura.id_colegio, FacturaDetalle.id_producto,
                FacturaDetalle.talla_individual, func.sum(FacturaDetalle.cantidad))
             .join(FacturaDetalle, FacturaDetalle.id_factura == Factura.id_factura)
             .filter(Factura.estado != 'ANULADA', Factura.fecha_factura >= corte)
             .group_by(Factura.id_colegio, FacturaDetalle.id_producto,
                       FacturaDetalle.talla_individual)
             .all())
    return {(cid, pid, talla): int(u or 0) for cid, pid, talla, u in filas}


# ── Analizadores por tipo ───────────────────────────────────────────────────
def _analizar_stock(cand, velmap):
    d = cand.get('datos', {})
    cid = d.get('id_colegio')
    pid = d.get('id_producto')
    # el detector guarda colegio/prenda por nombre; para la velocidad usamos ids
    vel = 0
    if pid is not None and cid is not None:
        vel = velmap.get((cid, pid, d.get('talla')), 0)
    stock = d.get('cantidad', 0)
    diario = vel / VENTANA_VENTAS if vel else 0
    cobertura = (stock / diario) if diario > 0 else None
    prenda, talla, cole = d.get('prenda', 'prenda'), d.get('talla', ''), d.get('colegio', '')

    # Sin ventas y con stock holgado (>3): está en la banda de vigilancia pero
    # NO es un riesgo real → se descarta para no generar ruido.
    if diario <= 0 and stock > UMBRAL_REAL_BAJO:
        return None, 0, None, None, None

    if diario > 0:
        impacto = _clamp(vel * 5)                       # 20 uds/sem → 100
        urgencia = _clamp(round(100 * (1 - (cobertura / (LEAD_TIME_DIAS * 2))))) if cobertura is not None else 60
        probabilidad = 75
        repo = max(0, int(math.ceil(diario * COBERTURA_OBJETIVO)) - stock)
        score = priority_score(impacto, urgencia, probabilidad)
        cov_txt = f'~{cobertura:.0f} día(s)' if cobertura is not None else 'poca'
        analisis = (f'Quedan {stock} y se vendieron {vel} en {VENTANA_VENTAS} días '
                    f'(~{diario:.1f}/día). Cobertura {cov_txt}; el proveedor tarda '
                    f'~{LEAD_TIME_DIAS} días → riesgo de quiebre antes de reponer.')
        if repo > 0:
            costo_est = _costo_estimado(cid, pid, repo)
            recomendacion = f'Preparar reposición de ~{repo} unidades de {prenda} T{talla} ({cole}).'
            if costo_est:
                recomendacion += f' Costo estimado ~${int(costo_est):,}.'.replace(',', '.')
            accion = {'tipo': 'crear_tarea',
                      'titulo': f'Reponer {prenda} T{talla} {cole} (~{repo} u)'[:200]}
            cand.setdefault('datos', {})['costo_estimado'] = costo_est
        else:
            recomendacion = f'Vigilar {prenda} T{talla}; la cobertura aún alcanza.'
            accion = None
        sev = _sev_por_score(score, minimo='PRECAUCION')
    else:
        # sin ventas recientes: bajo/agotado pero no urge
        agotado = (stock <= 0)
        impacto, urgencia, probabilidad = (40 if agotado else 20), (45 if agotado else 25), 40
        score = priority_score(impacto, urgencia, probabilidad)
        analisis = (f'{"Agotado" if agotado else f"Quedan {stock}"} pero sin ventas en '
                    f'{VENTANA_VENTAS} días: no urge reponer.')
        recomendacion = f'Revisar si {prenda} T{talla} sigue activa antes de reponer.'
        accion = None
        sev = _sev_por_score(score, minimo=('IMPORTANTE' if agotado else 'PRECAUCION'))

    return sev, score, analisis, recomendacion, accion


def _analizar_generico(cand):
    """Cartera, pedidos, ventas sin descuento: recomendación + acción preparable."""
    d = cand.get('datos', {})
    tipo = cand['tipo']
    sev = cand['severidad']
    score = _SCORE_POR_SEV.get(sev, 40)
    if tipo == 'factura_por_cobrar':
        analisis = f'Saldo pendiente hace {d.get("dias", "?")} días.'
        recomendacion = f'Contactar a {d.get("cliente") or "el cliente"} para cobrar el saldo.'
        accion = {'tipo': 'crear_tarea',
                  'titulo': f'Cobrar saldo {d.get("numero","")} a {d.get("cliente") or "cliente"}'[:200]}
    elif tipo in ('pedido_retrasado', 'fabricacion_retrasada'):
        analisis = f'Lleva {d.get("dias", "?")} día(s) sin resolverse.'
        recomendacion = 'Contactar al cliente / revisar el estado de producción.'
        ref = d.get('numero') or f'#{d.get("id_pedido", "")}'
        accion = {'tipo': 'crear_tarea', 'titulo': f'Revisar pedido atrasado {ref}'[:200]}
    elif tipo == 'venta_sin_descuento':
        analisis = 'Venta presencial pagada sin salida en el kardex.'
        recomendacion = (f'Revisar el kardex de {d.get("numero","")}; si falta, ajustar '
                         'el inventario de esas prendas.')
        accion = None  # revisar primero; no auto-sugerir un ajuste a ciegas
    else:
        analisis, recomendacion, accion = None, None, None
    return sev, score, analisis, recomendacion, accion


def analizar(cand, velmap=None):
    """Enriquece un candidato de evento con severidad ajustada, score,
    análisis, recomendación y acción sugerida. Devuelve el dict enriquecido."""
    if velmap is None:
        velmap = velocidad_ventas()
    if cand['tipo'] in ('stock_bajo', 'stock_agotado'):
        sev, score, analisis, recomendacion, accion = _analizar_stock(cand, velmap)
        if sev is None:                 # el analyzer decidió que no es riesgo real
            cand['descartar'] = True
            return cand
    else:
        sev, score, analisis, recomendacion, accion = _analizar_generico(cand)
    cand['severidad'] = sev
    cand['score'] = score
    cand['recomendacion'] = recomendacion
    datos = dict(cand.get('datos') or {})
    if analisis:
        datos['analisis'] = analisis
    if accion:
        datos['accion_sugerida'] = accion
    cand['datos'] = datos
    return cand
