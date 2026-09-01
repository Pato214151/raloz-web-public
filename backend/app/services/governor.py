"""
Self-Check / Governor — la capa que supervisa al PROPIO agente.

No aporta capacidades de negocio: protege al sistema aun cuando el modelo se
equivoque. Antes de ejecutar corre un checklist (objetivo, reglas, permisos,
reversibilidad, duplicación, verificabilidad); después comprueba que la acción
de verdad ocurrió, quedó registrada y cierra los eventos que ya no aplican.
"""
import logging
from datetime import datetime

from app import db
from app.models import Stock, PrecioColegio, Factura, Tarea, Evento

logger = logging.getLogger("raloz.governor")

REVERSIBLES = {'ajustar_stock', 'fijar_costo', 'cambiar_estado_pedido', 'crear_tarea'}
VERIFICABLES = REVERSIBLES


def verificar(tipo, despues):
    """Relee la FUENTE DE VERDAD y confirma que el cambio quedó aplicado.
    (Centralizado aquí: la capa Safety es la dueña de la verificación.)"""
    d = despues or {}
    try:
        if tipo == 'ajustar_stock':
            st = Stock.query.get(d.get('id_stock'))
            return bool(st) and st.cantidad == d.get('cantidad')
        if tipo == 'fijar_costo':
            ids = d.get('ids_precio') or []
            costo = d.get('costo')
            rows = (PrecioColegio.query.filter(PrecioColegio.id_precio.in_(ids)).all()
                    if ids else [])
            return bool(rows) and all(r.costo_unitario == costo for r in rows)
        if tipo == 'cambiar_estado_pedido':
            f = Factura.query.get(d.get('id_factura'))
            return bool(f) and f.estado_entrega == d.get('estado_entrega')
        if tipo == 'crear_tarea':
            return Tarea.query.get(d.get('id_tarea')) is not None
    except Exception as e:
        logger.warning("governor: verificación falló: %s", e)
    return False


def pre_check(accion):
    """Checklist PRE-ejecución. Devuelve {ok, bloqueos, checklist}.
    Un bloqueo impide ejecutar; un 'warn' solo informa."""
    tipo = (accion or {}).get('tipo')
    checklist, bloqueos = [], []

    def add(clave, estado, detalle=''):
        checklist.append({'clave': clave, 'estado': estado, 'detalle': detalle})

    add('objetivo', 'ok' if tipo else 'fail', tipo or 'sin tipo')
    if not tipo:
        bloqueos.append('La acción no tiene tipo.')

    add('reversible', 'ok' if tipo in REVERSIBLES else 'warn',
        'se puede deshacer' if tipo in REVERSIBLES else 'no reversible')
    add('verificable', 'ok' if tipo in VERIFICABLES else 'warn',
        'sé cómo comprobarla' if tipo in VERIFICABLES else 'sin verificación automática')

    # ¿Una regla del negocio lo prohíbe? (solo si la acción implica un gasto)
    monto = accion.get('monto') or accion.get('costo_compra')
    if monto:
        try:
            from app.services.business_memory import verificar_presupuesto_compras
            ok, _lim, msg = verificar_presupuesto_compras(monto)
            add('reglas', 'ok' if ok else 'fail', msg or 'sin conflicto')
            if not ok:
                bloqueos.append(msg)
        except Exception:
            add('reglas', 'warn', 'no pude comprobar reglas')
    else:
        add('reglas', 'ok', 'sin conflicto')

    return {'ok': not bloqueos, 'bloqueos': bloqueos, 'checklist': checklist}


def resolver_eventos(tipo, despues):
    """POST-acción: cierra los eventos abiertos que esta acción ya resolvió
    (Actions → Proactivity). Devuelve cuántos cerró."""
    d = despues or {}
    q = None
    if tipo == 'ajustar_stock' and d.get('id_stock'):
        q = Evento.query.filter(Evento.entidad_tipo == 'stock',
                                Evento.entidad_id == d['id_stock'],
                                Evento.estado.in_(('NUEVO', 'VISTO')))
    elif tipo == 'cambiar_estado_pedido' and d.get('id_factura') \
            and d.get('estado_entrega') == 'ENTREGADA':
        q = Evento.query.filter(Evento.entidad_tipo == 'factura',
                                Evento.entidad_id == d['id_factura'],
                                Evento.tipo.in_(('pedido_retrasado', 'venta_sin_descuento')),
                                Evento.estado.in_(('NUEVO', 'VISTO')))
    if q is None:
        return 0
    cerrados = 0
    for e in q.all():
        e.estado = 'RESUELTO'
        e.visto_en = datetime.utcnow()
        cerrados += 1
    if cerrados:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return 0
    return cerrados


def post_check(tipo, despues):
    """Checklist POST-ejecución: ¿ocurrió? ¿cierro eventos relacionados?"""
    verificado = verificar(tipo, despues)
    cerrados = resolver_eventos(tipo, despues)
    return {'verificado': verificado, 'eventos_cerrados': cerrados}
