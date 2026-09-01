"""
Event Engine — el "sistema nervioso" de RALOZ.

Escanea la operación real (stock, cartera, pedidos, ventas) y produce EVENTOS
priorizados por severidad. El Observador usa este motor para decir, sin que le
pregunten: "Jefe, detecté 3 cosas importantes".

Diseño:
  - Los DETECTORES son funciones puras: leen la BD y devuelven candidatos
    (dicts), sin efectos secundarios.
  - registrar_eventos() persiste los candidatos con dedup por clave_dedup: si
    ya existe un evento ABIERTO (NUEVO/VISTO) con esa clave, no lo duplica.
  - observar() corre todos los detectores, registra y devuelve el resumen
    priorizado.
"""
import logging
from datetime import date

from app import db
from app.models import (
    Stock, PrecioColegio, Producto, Colegio, Factura, FacturaDetalle,
    PedidoFabricacion, Evento,
)
from app.utils.inventario import stock_descontado_neto

logger = logging.getLogger("raloz.eventos")

UMBRAL_STOCK_BAJO = 3

_ORDEN_SEV = {'CRITICO': 0, 'IMPORTANTE': 1, 'PRECAUCION': 2, 'INFORMATIVO': 3}
EMOJI_SEV = {'CRITICO': '🔴', 'IMPORTANTE': '🟠', 'PRECAUCION': '🟡', 'INFORMATIVO': '🔵'}


def _cop(n):
    return f'${int(n or 0):,}'.replace(',', '.')


def _mapas():
    prod = {p.id_producto: p.nombre for p in Producto.query.all()}
    col = {c.id_colegio: c.nombre for c in Colegio.query.all()}
    return prod, col


# ── Detectores ────────────────────────────────────────────────────────────
def detectar_stock(umbral=UMBRAL_STOCK_BAJO, limite=60):
    """Prendas vendibles (con precio) agotadas o con stock bajo."""
    vendidos = {(pc.id_colegio, pc.id_producto) for pc in PrecioColegio.query.all()}
    if not vendidos:
        return []
    prod, col = _mapas()
    out = []
    for s in Stock.query.filter(Stock.cantidad <= umbral).all():
        if (s.id_colegio, s.id_producto) not in vendidos:
            continue
        nombre = prod.get(s.id_producto, f'Prod#{s.id_producto}')
        cole = col.get(s.id_colegio, '')
        cant = s.cantidad or 0
        if cant <= 0:
            out.append({
                'tipo': 'stock_agotado', 'severidad': Evento.IMPORTANTE,
                'titulo': f'Agotado: {nombre} T{s.talla_individual}',
                'detalle': f'{cole} · 0 unidades. Revisa si toca producir o reponer.',
                'entidad_tipo': 'stock', 'entidad_id': s.id_stock,
                'datos': {'colegio': cole, 'prenda': nombre,
                          'talla': s.talla_individual, 'cantidad': 0},
                'clave_dedup': f'stock_agotado:{s.id_stock}',
            })
        else:
            out.append({
                'tipo': 'stock_bajo', 'severidad': Evento.PRECAUCION,
                'titulo': f'Stock bajo: {nombre} T{s.talla_individual}',
                'detalle': f'{cole} · quedan {cant} unidad(es).',
                'entidad_tipo': 'stock', 'entidad_id': s.id_stock,
                'datos': {'colegio': cole, 'prenda': nombre,
                          'talla': s.talla_individual, 'cantidad': cant},
                'clave_dedup': f'stock_bajo:{s.id_stock}',
            })
    out.sort(key=lambda e: _ORDEN_SEV[e['severidad']])
    return out[:limite]


def detectar_cartera(dias_importante=15, dias_critico=30):
    """Facturas con saldo pendiente que ya llevan días sin cobrarse."""
    hoy = date.today()
    out = []
    facs = Factura.query.filter(Factura.estado == 'PENDIENTE',
                                Factura.saldo_pendiente > 0).all()
    for f in facs:
        dias = (hoy - (f.fecha_factura or hoy)).days
        if dias < dias_importante:
            continue
        sev = Evento.CRITICO if dias >= dias_critico else Evento.IMPORTANTE
        saldo = int(f.saldo_pendiente or 0)
        out.append({
            'tipo': 'factura_por_cobrar', 'severidad': sev,
            'titulo': f'Saldo por cobrar: {f.numero_factura}',
            'detalle': f'{f.cliente_nombre or "Cliente"} debe {_cop(saldo)} hace {dias} días.',
            'entidad_tipo': 'factura', 'entidad_id': f.id_factura,
            'datos': {'numero': f.numero_factura, 'saldo': saldo, 'dias': dias,
                      'cliente': f.cliente_nombre},
            'clave_dedup': f'cobrar:{f.id_factura}',
        })
    return out


def detectar_pedidos_retrasados(dias_web=5):
    """Pedidos web sin entregar hace días y fabricaciones con fecha vencida."""
    hoy = date.today()
    out = []
    facs = Factura.query.filter(Factura.canal == 'WEB',
                                Factura.estado != 'ANULADA',
                                Factura.estado_entrega != 'ENTREGADA').all()
    for f in facs:
        dias = (hoy - (f.fecha_factura or hoy)).days
        if dias < dias_web:
            continue
        out.append({
            'tipo': 'pedido_retrasado', 'severidad': Evento.IMPORTANTE,
            'titulo': f'Pedido web sin entregar: {f.numero_factura}',
            'detalle': f'{f.cliente_nombre or "Cliente"} · {dias} días en "{f.estado_entrega}".',
            'entidad_tipo': 'factura', 'entidad_id': f.id_factura,
            'datos': {'numero': f.numero_factura, 'dias': dias,
                      'estado_entrega': f.estado_entrega},
            'clave_dedup': f'retraso_pedido:{f.id_factura}',
        })
    fabs = PedidoFabricacion.query.filter(
        PedidoFabricacion.estado != 'entregado',
        PedidoFabricacion.fecha_estimada.isnot(None),
        PedidoFabricacion.fecha_estimada < hoy,
    ).all()
    for pf in fabs:
        dias = (hoy - pf.fecha_estimada).days
        out.append({
            'tipo': 'fabricacion_retrasada', 'severidad': Evento.IMPORTANTE,
            'titulo': f'Fabricación vencida (#{pf.id_pedido})',
            'detalle': f'Debía estar lista hace {dias} día(s) · estado "{pf.estado}".',
            'entidad_tipo': 'pedido_fabricacion', 'entidad_id': pf.id_pedido,
            'datos': {'id_pedido': pf.id_pedido, 'dias': dias, 'estado': pf.estado},
            'clave_dedup': f'retraso_fab:{pf.id_pedido}',
        })
    return out


def detectar_ventas_sin_descuento(dias=7):
    """Ventas PRESENCIALES pagadas que NO descontaron inventario (anomalía).
    Conservador: presencial siempre debería descontar; si no hay ninguna
    SALIDA en el kardex, hay algo que revisar."""
    from datetime import timedelta
    corte = date.today() - timedelta(days=dias)
    out = []
    facs = Factura.query.filter(Factura.estado == 'PAGADA',
                                Factura.canal == 'PRESENCIAL',
                                Factura.fecha_factura >= corte).all()
    for f in facs:
        tiene_items = FacturaDetalle.query.filter_by(id_factura=f.id_factura).count() > 0
        if not tiene_items:
            continue
        neto = stock_descontado_neto(f.numero_factura, f.id_colegio)
        if not neto:  # ninguna SALIDA asociada → sospechoso
            out.append({
                'tipo': 'venta_sin_descuento', 'severidad': Evento.IMPORTANTE,
                'titulo': f'Revisar inventario: {f.numero_factura}',
                'detalle': 'Venta presencial pagada sin descuento de inventario en el kardex.',
                'entidad_tipo': 'factura', 'entidad_id': f.id_factura,
                'datos': {'numero': f.numero_factura, 'cliente': f.cliente_nombre},
                'clave_dedup': f'sin_descuento:{f.id_factura}',
            })
    return out


DETECTORES = (
    detectar_stock,
    detectar_cartera,
    detectar_pedidos_retrasados,
    detectar_ventas_sin_descuento,
)


# ── Registro (con dedup) y observación ──────────────────────────────────────
def registrar_eventos(candidatos):
    """Persiste candidatos evitando duplicar eventos ya abiertos (dedup).
    Devuelve la lista de eventos NUEVOS creados en esta pasada. No hace commit
    del caller externo: hace su propio commit."""
    if not candidatos:
        return []
    claves = [c['clave_dedup'] for c in candidatos]
    abiertos = {
        e.clave_dedup for e in Evento.query
        .filter(Evento.clave_dedup.in_(claves),
                Evento.estado.in_(('NUEVO', 'VISTO'))).all()
    }
    nuevos = []
    for c in candidatos:
        if c['clave_dedup'] in abiertos:
            continue
        ev = Evento(
            tipo=c['tipo'], severidad=c['severidad'], titulo=c['titulo'][:200],
            detalle=(c.get('detalle') or '')[:500] or None,
            entidad_tipo=c.get('entidad_tipo'), entidad_id=c.get('entidad_id'),
            clave_dedup=c['clave_dedup'], estado='NUEVO',
        )
        ev.set_datos(c.get('datos'))
        db.session.add(ev)
        nuevos.append(ev)
        abiertos.add(c['clave_dedup'])  # evita duplicar dentro de la misma pasada
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("event_engine: no se pudieron registrar eventos: %s", e)
        return []
    return nuevos


def escanear():
    """Corre todos los detectores y devuelve la lista plana de candidatos."""
    candidatos = []
    for det in DETECTORES:
        try:
            candidatos.extend(det() or [])
        except Exception as e:
            logger.warning("event_engine: detector %s falló: %s", det.__name__, e)
    return candidatos


def observar(persistir=True):
    """OBSERVAR → EVALUAR → PRIORIZAR. Corre los detectores, (opcionalmente)
    registra los eventos nuevos y devuelve el resumen priorizado de todo lo
    que está ABIERTO (NUEVO/VISTO)."""
    candidatos = escanear()
    nuevos = registrar_eventos(candidatos) if persistir else []
    abiertos = (Evento.query
                .filter(Evento.estado.in_(('NUEVO', 'VISTO')))
                .all())
    abiertos.sort(key=lambda e: (_ORDEN_SEV.get(e.severidad, 9), -(e.id_evento or 0)))
    resumen = {'CRITICO': 0, 'IMPORTANTE': 0, 'PRECAUCION': 0, 'INFORMATIVO': 0}
    for e in abiertos:
        resumen[e.severidad] = resumen.get(e.severidad, 0) + 1
    return {
        'generado_en': date.today().isoformat(),
        'nuevos': len(nuevos),
        'total_abierto': len(abiertos),
        'resumen': resumen,
        'hay_algo': len(abiertos) > 0,
        'eventos': [e.to_dict() for e in abiertos],
    }
