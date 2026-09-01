"""
Business Memory — RALOZ conoce la POLÍTICA del negocio, no solo los datos.

Tres piezas:
  - Reglas del negocio (políticas): 'no comprar más de $10M/mes'.
  - Memoria de decisiones/preferencias: 'prefiero el proveedor X'.
  - Objetivos persistentes: 'vender $30M en septiembre' (progreso en vivo).

También arma el resumen Home / Daily Briefing ('Buenos días, Jefe').
"""
import logging
from datetime import date
from calendar import monthrange

from sqlalchemy import func

from app import db
from app.models import (
    ReglaNegocio, MemoriaNegocio, Objetivo, Factura,
)

logger = logging.getLogger("raloz.business")


def _cop(n):
    return f'${int(n or 0):,}'.replace(',', '.')


# ── Reglas ──────────────────────────────────────────────────────────────────
def reglas_activas():
    return (ReglaNegocio.query.filter_by(activa=True)
            .order_by(ReglaNegocio.categoria, ReglaNegocio.id_regla).all())


def reglas_texto():
    """Texto compacto de las reglas activas para inyectar en el prompt."""
    rs = reglas_activas()
    if not rs:
        return ''
    return '\n'.join(f'- [{r.categoria}] {r.texto}' for r in rs)


def presupuesto_compras_mensual():
    """Devuelve (limite, regla) si existe una regla de tope de compras mensual."""
    for r in reglas_activas():
        if r.categoria == 'COMPRAS':
            p = r.params or {}
            lim = p.get('limite')
            if lim and (p.get('periodo', 'mensual') == 'mensual'):
                return float(lim), r
    return None, None


def verificar_presupuesto_compras(monto):
    """(permitido, limite, mensaje). Si no hay regla, siempre permitido."""
    limite, _regla = presupuesto_compras_mensual()
    if not limite:
        return True, None, None
    if (monto or 0) <= limite:
        return True, limite, None
    return False, limite, (f'Supera el presupuesto de compras registrado '
                           f'({_cop(limite)}/mes).')


# ── Memoria de decisiones ─────────────────────────────────────────────────────
def memoria_activa():
    return (MemoriaNegocio.query.filter_by(activa=True)
            .order_by(MemoriaNegocio.id_memoria).all())


def memoria_texto():
    ms = memoria_activa()
    if not ms:
        return ''
    return '\n'.join(f'- [{m.tipo}] {m.texto}' for m in ms)


# ── Objetivos ─────────────────────────────────────────────────────────────────
def _rango(anio, mes):
    if mes:
        return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])
    return date(anio, 1, 1), date(anio, 12, 31)


def _ventas_periodo(anio, mes):
    ini, fin = _rango(anio, mes)
    total = (db.session.query(func.coalesce(func.sum(Factura.total), 0))
             .filter(Factura.estado != 'ANULADA',
                     Factura.fecha_factura >= ini, Factura.fecha_factura <= fin)
             .scalar())
    return float(total or 0)


def progreso_objetivos():
    """Cada objetivo activo con su avance calculado en vivo."""
    out = []
    for o in Objetivo.query.filter_by(activa=True).order_by(Objetivo.id_objetivo).all():
        actual = _ventas_periodo(o.anio, o.mes) if o.tipo == 'VENTAS' else 0
        pct = round(actual / o.meta * 100) if o.meta else 0
        # proyección simple: ¿alcanza al ritmo actual? (solo para el mes en curso)
        proyecta_ok = None
        hoy = date.today()
        if o.mes and o.anio == hoy.year and o.mes == hoy.month:
            dias_mes = monthrange(o.anio, o.mes)[1]
            if hoy.day > 0:
                proyeccion = actual / hoy.day * dias_mes
                proyecta_ok = proyeccion >= o.meta
        out.append({
            'id_objetivo': o.id_objetivo, 'tipo': o.tipo,
            'descripcion': o.descripcion, 'meta': o.meta, 'actual': actual,
            'pct': pct, 'anio': o.anio, 'mes': o.mes, 'proyecta_ok': proyecta_ok,
        })
    return out


# ── Home / Daily Briefing ─────────────────────────────────────────────────────
def resumen_home():
    """'Buenos días, Jefe': alertas + metas + cartera + recomendaciones del día."""
    from app.services.event_engine import observar
    obs = observar(persistir=True)
    metas = progreso_objetivos()
    cartera = (db.session.query(func.coalesce(func.sum(Factura.saldo_pendiente), 0))
               .filter(Factura.estado == 'PENDIENTE').scalar()) or 0
    recomendaciones = [it.get('recomendacion') for it in obs.get('items', [])
                       if it.get('recomendacion')][:3]
    inv_criticas = sum(1 for it in obs.get('items', [])
                       if it.get('tipo') in ('stock_agotado', 'stock_bajo', 'grupo_stock'))
    return {
        'generado_en': date.today().isoformat(),
        'alertas': obs.get('resumen', {}),
        'total_alertas': obs.get('total_abierto', 0),
        'metas': metas,
        'cartera_pendiente': float(cartera or 0),
        'inventario_criticas': inv_criticas,
        'recomendaciones': recomendaciones,
        'modo': obs.get('modo'),
    }
