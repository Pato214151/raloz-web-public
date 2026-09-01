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
import threading
from datetime import date, datetime

from app import db
from app.models import (
    Stock, PrecioColegio, Producto, Colegio, Factura, FacturaDetalle,
    PedidoFabricacion, Evento,
)
from app.utils.inventario import stock_descontado_neto

logger = logging.getLogger("raloz.eventos")

UMBRAL_STOCK_BAJO = 3     # "hard low": bajo aunque no tenga ventas
UMBRAL_WATCH = 10         # banda de vigilancia: el analyzer decide si es riesgo real

_ORDEN_SEV = {'CRITICO': 0, 'IMPORTANTE': 1, 'PRECAUCION': 2, 'INFORMATIVO': 3}
EMOJI_SEV = {'CRITICO': '🔴', 'IMPORTANTE': '🟠', 'PRECAUCION': '🟡', 'INFORMATIVO': '🔵'}


def _cop(n):
    return f'${int(n or 0):,}'.replace(',', '.')


def _mapas():
    prod = {p.id_producto: p.nombre for p in Producto.query.all()}
    col = {c.id_colegio: c.nombre for c in Colegio.query.all()}
    return prod, col


# ── Detectores ────────────────────────────────────────────────────────────
def detectar_stock(umbral=UMBRAL_WATCH, limite=60):
    """Prendas vendibles (con precio) agotadas o dentro de la banda de vigilancia.
    El analyzer decide después si un stock >3 realmente es riesgo (por velocidad)."""
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
                          'talla': s.talla_individual, 'cantidad': 0,
                          'id_colegio': s.id_colegio, 'id_producto': s.id_producto},
                'clave_dedup': f'stock_agotado:{s.id_stock}',
            })
        else:
            out.append({
                'tipo': 'stock_bajo', 'severidad': Evento.PRECAUCION,
                'titulo': f'Stock bajo: {nombre} T{s.talla_individual}',
                'detalle': f'{cole} · quedan {cant} unidad(es).',
                'entidad_tipo': 'stock', 'entidad_id': s.id_stock,
                'datos': {'colegio': cole, 'prenda': nombre,
                          'talla': s.talla_individual, 'cantidad': cant,
                          'id_colegio': s.id_colegio, 'id_producto': s.id_producto},
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
            score=c.get('score'),
            recomendacion=(c.get('recomendacion') or None) and c['recomendacion'][:500],
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


# Tipos que reflejan el estado ACTUAL de la BD → si el hecho ya no aparece en
# un escaneo, el problema se resolvió solo y el evento se auto-cierra.
_AUTO_RESUELVE = {'stock_bajo', 'stock_agotado', 'factura_por_cobrar',
                  'pedido_retrasado', 'fabricacion_retrasada', 'venta_sin_descuento'}


def escanear(analizar_eventos=True):
    """Corre los detectores y (por defecto) analiza cada candidato para darle
    contexto, score y recomendación. Devuelve la lista plana de candidatos."""
    from app.services.event_analyzer import analizar, velocidad_ventas
    candidatos = []
    for det in DETECTORES:
        try:
            candidatos.extend(det() or [])
        except Exception as e:
            logger.warning("event_engine: detector %s falló: %s", det.__name__, e)
    if analizar_eventos and candidatos:
        try:
            velmap = velocidad_ventas()
            candidatos = [analizar(c, velmap) for c in candidatos]
            candidatos = [c for c in candidatos if not c.get('descartar')]
        except Exception as e:
            logger.warning("event_engine: análisis falló: %s", e)
    return candidatos


def reconciliar(candidatos):
    """MEMORIA: cierra (RESUELTO) los eventos abiertos cuyo problema ya no
    aparece en el escaneo actual. Así RALOZ no repite algo que ya se solucionó."""
    from datetime import datetime as _dt
    claves_actuales = {c['clave_dedup'] for c in candidatos}
    abiertos = Evento.query.filter(Evento.estado.in_(('NUEVO', 'VISTO'))).all()
    cerrados = 0
    for e in abiertos:
        if e.tipo in _AUTO_RESUELVE and e.clave_dedup not in claves_actuales:
            e.estado = 'RESUELTO'
            e.visto_en = _dt.utcnow()
            cerrados += 1
    if cerrados:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return cerrados


def _agrupar(eventos):
    """Agrupa varios eventos de stock de la misma prenda+colegio en una sola
    alerta ('riesgo de reposición en 4 tallas'). El resto pasa tal cual."""
    grupos, sueltos = {}, []
    for e in eventos:
        d = e.datos_dict or {}
        if e.tipo in ('stock_bajo', 'stock_agotado') and d.get('id_producto'):
            grupos.setdefault((d.get('id_colegio'), d['id_producto']), []).append(e)
        else:
            sueltos.append(e)
    items = []
    for _, evs in grupos.items():
        if len(evs) == 1:
            sueltos.append(evs[0])
            continue
        evs.sort(key=lambda e: (_ORDEN_SEV.get(e.severidad, 9), -(e.score or 0)))
        d0 = evs[0].datos_dict or {}
        tallas = [ (e.datos_dict or {}).get('talla') for e in evs ]
        sev = evs[0].severidad
        score = max((e.score or 0) for e in evs)
        rec = next((e.recomendacion for e in evs if e.recomendacion), None)
        items.append({
            'agrupado': True, 'severidad': sev, 'score': score,
            'titulo': f'{d0.get("prenda","Prenda")} ({d0.get("colegio","")}): '
                      f'reposición en {len(evs)} tallas',
            'detalle': 'Tallas por debajo del objetivo: ' + ', '.join(str(t) for t in tallas) + '.',
            'recomendacion': rec,
            'ids': [e.id_evento for e in evs],
            'tipo': 'grupo_stock',
        })
    for e in sueltos:
        items.append(e.to_dict())
    items.sort(key=lambda x: (_ORDEN_SEV.get(x.get('severidad'), 9), -(x.get('score') or 0)))
    return items


def observar(persistir=True):
    """OBSERVAR → ANALIZAR → PRIORIZAR → (recordar). Corre los detectores,
    analiza y puntúa, cierra lo ya resuelto, registra lo nuevo y devuelve el
    resumen priorizado y AGRUPADO de todo lo que sigue abierto."""
    candidatos = escanear(analizar_eventos=True)
    cerrados = 0
    nuevos = []
    if persistir:
        cerrados = reconciliar(candidatos)
        nuevos = registrar_eventos(candidatos)
        try:
            _auto_accion(nuevos)     # autonomía controlada (solo si el modo lo permite)
        except Exception as e:
            logger.warning("event_engine: auto-acción falló: %s", e)
    abiertos = Evento.query.filter(Evento.estado.in_(('NUEVO', 'VISTO'))).all()
    abiertos.sort(key=lambda e: (_ORDEN_SEV.get(e.severidad, 9), -(e.score or 0)))
    resumen = {'CRITICO': 0, 'IMPORTANTE': 0, 'PRECAUCION': 0, 'INFORMATIVO': 0}
    for e in abiertos:
        resumen[e.severidad] = resumen.get(e.severidad, 0) + 1
    nuevos_relev = [e for e in nuevos if e.severidad in ('CRITICO', 'IMPORTANTE')]
    return {
        'generado_en': date.today().isoformat(),
        'nuevos': len(nuevos),
        'nuevos_relevantes': len(nuevos_relev),
        'nuevo_top': (nuevos_relev[0].titulo if nuevos_relev else None),
        'resueltos': cerrados,
        'total_abierto': len(abiertos),
        'resumen': resumen,
        'hay_algo': len(abiertos) > 0,
        'modo': modo_observador(),
        'items': _agrupar(abiertos),                    # agrupado + priorizado (para mostrar)
        'eventos': [e.to_dict() for e in abiertos],     # crudo (compat)
    }


# ─────────────────────────────────────────────────────────────────────────
#  Modos de autonomía · Auto-acción controlada · Push · Tiempo real
# ─────────────────────────────────────────────────────────────────────────
# SUGERIR  = detecta → analiza → recomienda (por defecto).
# PREPARAR = igual, pero deja la acción lista para confirmar en 1 clic.
# AUTONOMO = ejecuta SOLO acciones de bajo riesgo previamente autorizadas
#            (crear recordatorio). Nunca cambios de stock/costo/estado ni compras.
MODO_SUGERIR, MODO_PREPARAR, MODO_AUTONOMO = 'SUGERIR', 'PREPARAR', 'AUTONOMO'
_MODOS = (MODO_SUGERIR, MODO_PREPARAR, MODO_AUTONOMO)
# Únicas acciones que el modo AUTÓNOMO puede ejecutar solo (bajo riesgo, reversible):
_AUTO_WHITELIST = {'crear_tarea'}
_SCORE_AUTO = 80   # solo eventos realmente prioritarios


def modo_observador():
    from app.models import ConfigSitio
    m = (ConfigSitio.get('observador_modo', MODO_SUGERIR) or MODO_SUGERIR).upper()
    return m if m in _MODOS else MODO_SUGERIR


def set_modo_observador(modo):
    from app.models import ConfigSitio
    modo = str(modo or '').upper()
    if modo not in _MODOS:
        return None
    ConfigSitio.set('observador_modo', modo)
    db.session.commit()
    return modo


def _auto_accion(nuevos):
    """Autonomía CONTROLADA: en modo AUTÓNOMO, ejecuta las acciones de bajo
    riesgo (crear recordatorio) de los eventos nuevos de alta prioridad, y las
    deja en la bitácora (auditable + reversible). Nada más se ejecuta solo."""
    if modo_observador() != MODO_AUTONOMO or not nuevos:
        return
    from app.models import Tarea, Usuario, AccionAsistente
    admin = Usuario.query.filter_by(rol='administrador').first()
    if not admin:
        return  # sin un dueño a quien atribuirlo, no actuamos
    for ev in nuevos:
        if (ev.score or 0) < _SCORE_AUTO:
            continue
        accion = (ev.datos_dict or {}).get('accion_sugerida') or {}
        if accion.get('tipo') not in _AUTO_WHITELIST:
            continue
        titulo = str(accion.get('titulo', ''))[:200]
        if not titulo:
            continue
        t = Tarea(titulo=titulo, descripcion=f'[Observador] {ev.recomendacion or ""}'[:500],
                  creada_por=admin.id_usuario)
        db.session.add(t)
        db.session.flush()
        acc = AccionAsistente(
            tipo='crear_tarea', descripcion=f'[Observador·auto] {titulo}',
            reversible=True, verificado=(Tarea.query.get(t.id_tarea) is not None),
            resultado='VERIFICADA', usuario='[Observador]')
        acc.set_antes({})
        acc.set_despues({'id_tarea': t.id_tarea})
        db.session.add(acc)
        ev.estado = 'VISTO'
        ev.visto_en = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _texto_resumen(r):
    partes = []
    for sev, et in (('CRITICO', '🔴'), ('IMPORTANTE', '🟠'), ('PRECAUCION', '🟡')):
        n = r['resumen'].get(sev, 0)
        if n:
            partes.append(f'{et} {n}')
    return ' · '.join(partes) if partes else 'Todo en orden'


def _push(titulo, cuerpo):
    try:
        from app.api.push import enviar_push_a_todos
        return enviar_push_a_todos(titulo, cuerpo, url='/asistente', tag='observador')
    except Exception as e:
        logger.warning("event_engine: push falló: %s", e)
        return 0


# Coalescing (la "cola"): varios disparos seguidos colapsan en UN solo escaneo,
# así 5 eventos simultáneos no producen 5 respuestas.
_timer_lock = threading.Lock()
_timer = {'t': None}


def disparar(app, motivo='evento', delay=20):
    """Tiempo real: agenda un escaneo del Observador tras `delay` s. Si ya hay
    uno agendado, no agenda otro (coalesce). Best-effort; nunca lanza al caller."""
    def _run():
        with _timer_lock:
            _timer['t'] = None
        try:
            with app.app_context():
                r = observar(persistir=True)
                if r.get('nuevos_relevantes'):
                    top = r.get('nuevo_top') or 'Hay algo que revisar'
                    _push('RALOZ · Alerta', f'{top} — {_texto_resumen(r)}')
        except Exception as e:
            logger.warning("event_engine: disparo (%s) falló: %s", motivo, e)

    try:
        with _timer_lock:
            if _timer['t'] is not None:
                return  # ya hay un escaneo en camino → coalesce
            t = threading.Timer(delay, _run)
            t.daemon = True
            _timer['t'] = t
            t.start()
    except Exception as e:
        logger.warning("event_engine: no se pudo agendar disparo: %s", e)


def push_resumen(r, titulo='RALOZ · Buenos días, Jefe'):
    """Manda un push con el resumen del Observador SOLO si hay algo relevante
    (🔴/🟠). Devuelve cuántos push se enviaron."""
    relev = r['resumen'].get('CRITICO', 0) + r['resumen'].get('IMPORTANTE', 0)
    if not relev:
        return 0
    return _push(titulo, f'Revisé el negocio: {_texto_resumen(r)}. Toca mirarlo.')


def resumen_matutino(app):
    """'Buenos días, Jefe': corre el Observador y, si hay algo relevante, manda
    un push con el resumen. Pensado para el cron de la mañana."""
    with app.app_context():
        r = observar(persistir=True)
        push_resumen(r)
        return r
