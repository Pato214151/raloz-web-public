"""
Motor de reglas de automatización (Fase 3).
Evalúa las reglas activas; lo invoca un daemon de run.py cada pocas horas.
Las reglas son aditivas y seguras (no mutan productos): por ahora, alertas.
"""
import os
import logging
from datetime import datetime, timedelta

from app import db
from app.models import ReglaAuto, Stock, Producto, Colegio, WaConversacion, WaMensaje
from app.services.wa_send import enviar_whatsapp

logger = logging.getLogger(__name__)

# Autores que NO son un asesor humano (los pone el propio sistema)
_AUTORES_AUTOMATICOS = ('bot', 'sistema', 'aviso', 'regla')


def productos_stock_bajo(umbral=5):
    """Stock por (colegio, producto, talla) con 0 < cantidad <= umbral, de
    productos y colegios activos. Ordenado del más crítico al menos."""
    rows = (
        db.session.query(Stock, Producto, Colegio)
        .join(Producto, Stock.id_producto == Producto.id_producto)
        .join(Colegio, Stock.id_colegio == Colegio.id_colegio)
        .filter(
            Stock.cantidad > 0, Stock.cantidad <= umbral,
            Producto.activo.is_(True), Colegio.activo.is_(True),
        )
        .order_by(Stock.cantidad.asc())
        .all()
    )
    return [{
        'producto': p.nombre, 'colegio': c.nombre,
        'talla': s.talla_individual, 'cantidad': s.cantidad,
    } for s, p, c in rows]


def _regla_alerta_stock_bajo(regla):
    """Envía al admin un resumen de stock bajo. Throttle: máx 1 vez cada 24 h."""
    ahora = datetime.utcnow()
    if regla.ultima_ejecucion and ahora - regla.ultima_ejecucion < timedelta(hours=24):
        return False
    umbral = int(regla.get_config().get('umbral', 5))
    bajos = productos_stock_bajo(umbral)
    regla.ultima_ejecucion = ahora
    db.session.commit()
    if not bajos:
        return False
    admin = os.getenv('ADMIN_WHATSAPP', '').strip()
    if not admin:
        return False
    lineas = [f'⚠️ *Stock bajo* (≤ {umbral} unidades):']
    for b in bajos[:20]:
        lineas.append(f"• {b['producto']} ({b['colegio']}) talla {b['talla']}: {b['cantidad']}")
    if len(bajos) > 20:
        lineas.append(f'…y {len(bajos) - 20} más.')
    return enviar_whatsapp(admin, '\n'.join(lineas), autor='regla')


def _regla_volver_a_bot(regla):
    """Cuando un asesor responde desde el panel, el chat queda en 'modo humano' y
    el bot deja de contestarle a ese cliente. Esta regla lo devuelve a 'bot' tras
    N horas sin que un humano escriba, para que el bot vuelva a atender solo."""
    horas = int(regla.get_config().get('horas', 12))
    corte = datetime.utcnow() - timedelta(hours=horas)
    devueltos = 0

    for conv in WaConversacion.query.filter_by(modo='humano').all():
        ultimo_humano = (
            WaMensaje.query
            .filter(
                WaMensaje.chat_id == conv.chat_id,
                WaMensaje.direccion == 'out',
                WaMensaje.autor.notin_(_AUTORES_AUTOMATICOS),
            )
            .order_by(WaMensaje.fecha.desc())
            .first()
        )
        # Sin mensajes de asesor, usamos la última actividad del chat
        referencia = ultimo_humano.fecha if ultimo_humano else conv.ultima_fecha
        if referencia and referencia < corte:
            conv.modo = 'bot'
            devueltos += 1

    regla.ultima_ejecucion = datetime.utcnow()
    db.session.commit()
    if devueltos:
        logger.info('[reglas] %d chat(s) devueltos a modo bot', devueltos)
    return devueltos


_EJECUTORES = {
    'alerta_stock_bajo': _regla_alerta_stock_bajo,
    'volver_a_bot': _regla_volver_a_bot,
}


def evaluar_reglas():
    """Evalúa todas las reglas activas (lo llama el daemon). Tolerante a fallos."""
    for regla in ReglaAuto.query.filter_by(activa=True).all():
        fn = _EJECUTORES.get(regla.clave)
        if not fn:
            continue
        try:
            fn(regla)
        except Exception as e:  # noqa: BLE001 — una regla no debe tumbar el daemon
            logger.error('[reglas] %s falló: %s', regla.clave, e)
            db.session.rollback()
