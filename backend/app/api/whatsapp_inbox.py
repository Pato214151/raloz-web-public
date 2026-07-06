"""
Bandeja de WhatsApp (inbox) dentro del panel.

Dos tipos de acceso:
  1. El BOT (bot_meta.py, otro servicio) registra cada mensaje y consulta el modo
     de la conversación. Se autentica con un secreto compartido en la cabecera
     X-Bot-Token (variable de entorno WA_LOG_TOKEN, igual en el bot y el backend).
  2. El PANEL (asesores) lista conversaciones, lee mensajes, responde y decide si
     el bot o un humano atiende. Se autentica con JWT (rol admin/vendedor/cajero).

Enviar mensajes desde el panel usa la WhatsApp Cloud API (Meta), así que el backend
necesita WHATSAPP_TOKEN y PHONE_NUMBER_ID en su entorno (las mismas del bot).
"""

import os
from datetime import datetime

import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app import db
from app.models import WaConversacion, WaMensaje
from app.utils.decorators import rol_requerido, get_current_identity

wa_inbox_bp = Blueprint('wa_inbox', __name__)

GRAPH_VERSION = os.getenv('GRAPH_VERSION', 'v21.0')


# ─────────────────────── Autenticación del bot ───────────────────────
def _bot_autorizado():
    esperado = os.getenv('WA_LOG_TOKEN', '')
    return bool(esperado) and request.headers.get('X-Bot-Token', '') == esperado


def _upsert_conversacion(chat_id, nombre=None):
    conv = db.session.get(WaConversacion, chat_id)
    if conv is None:
        conv = WaConversacion(chat_id=chat_id, nombre=nombre, modo='bot')
        db.session.add(conv)
    elif nombre and not conv.nombre:
        conv.nombre = nombre
    return conv


# ─────────────────────── Endpoints para el BOT ───────────────────────
@wa_inbox_bp.route('/log', methods=['POST'])
def log_mensaje():
    """El bot registra un mensaje (entrante o saliente). Devuelve el modo actual
    de la conversación para que el bot sepa si debe responder o quedarse callado."""
    if not _bot_autorizado():
        return jsonify({'error': 'no autorizado'}), 401

    data = request.get_json(silent=True) or {}
    chat_id = (data.get('chat_id') or '').strip()
    direccion = (data.get('direccion') or 'in').strip()
    texto = data.get('texto') or ''
    autor = data.get('autor') or ('cliente' if direccion == 'in' else 'bot')
    nombre = data.get('nombre')

    if not chat_id or direccion not in ('in', 'out'):
        return jsonify({'error': 'chat_id y direccion (in|out) requeridos'}), 400

    conv = _upsert_conversacion(chat_id, nombre)
    conv.ultimo_mensaje = texto[:500]
    conv.ultima_fecha = datetime.utcnow()
    if direccion == 'in':
        conv.no_leidos = (conv.no_leidos or 0) + 1
    # El bot puede pedir el paso a humano (ej: el cliente pidió un asesor)
    set_modo = data.get('set_modo')
    if set_modo in ('bot', 'humano'):
        conv.modo = set_modo

    db.session.add(WaMensaje(
        chat_id=chat_id, direccion=direccion, texto=texto, autor=autor,
        media_tipo=data.get('media_tipo'),
        media_b64=data.get('media_b64'),
    ))
    db.session.commit()
    return jsonify({'ok': True, 'modo': conv.modo or 'bot'})


@wa_inbox_bp.route('/modo/<chat_id>', methods=['GET'])
def consultar_modo(chat_id):
    """El bot pregunta si una conversación está en modo 'bot' o 'humano'."""
    if not _bot_autorizado():
        return jsonify({'error': 'no autorizado'}), 401
    conv = db.session.get(WaConversacion, chat_id)
    return jsonify({'modo': (conv.modo if conv else 'bot')})


# ─────────────────────── Endpoints para el PANEL ───────────────────────
@wa_inbox_bp.route('/conversaciones', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def listar_conversaciones():
    convs = (WaConversacion.query
             .order_by(WaConversacion.ultima_fecha.desc())
             .limit(200).all())
    return jsonify([c.to_dict() for c in convs])


@wa_inbox_bp.route('/no-leidos', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def total_no_leidos():
    total = db.session.query(db.func.coalesce(db.func.sum(WaConversacion.no_leidos), 0)).scalar()
    return jsonify({'no_leidos': int(total or 0)})


@wa_inbox_bp.route('/conversaciones/<chat_id>/mensajes', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def listar_mensajes(chat_id):
    msgs = (WaMensaje.query
            .filter_by(chat_id=chat_id)
            .order_by(WaMensaje.fecha.asc())
            .limit(500).all())
    # abrir la conversación marca como leídos
    conv = db.session.get(WaConversacion, chat_id)
    if conv and conv.no_leidos:
        conv.no_leidos = 0
        db.session.commit()
    return jsonify([m.to_dict() for m in msgs])


@wa_inbox_bp.route('/media/<int:id_mensaje>', methods=['GET'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def obtener_media(id_mensaje):
    """Devuelve el adjunto (imagen/archivo) de un mensaje, en base64."""
    msg = db.session.get(WaMensaje, id_mensaje)
    if not msg or not msg.media_b64:
        return jsonify({'error': 'sin adjunto'}), 404
    return jsonify({'media_tipo': msg.media_tipo or 'image', 'media_b64': msg.media_b64})


@wa_inbox_bp.route('/conversaciones/<chat_id>/modo', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def cambiar_modo(chat_id):
    """Pasa la conversación a 'humano' (el bot se calla) o 'bot' (responde solo)."""
    data = request.get_json(silent=True) or {}
    modo = (data.get('modo') or '').strip()
    if modo not in ('bot', 'humano'):
        return jsonify({'error': "modo debe ser 'bot' o 'humano'"}), 400
    conv = _upsert_conversacion(chat_id)
    conv.modo = modo
    db.session.commit()
    return jsonify({'ok': True, 'modo': modo})


@wa_inbox_bp.route('/conversaciones/<chat_id>/enviar', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def enviar_mensaje(chat_id):
    """Un asesor responde desde el panel. Envía por la Cloud API, guarda el mensaje
    y deja la conversación en modo 'humano'."""
    data = request.get_json(silent=True) or {}
    texto = (data.get('texto') or '').strip()
    if not texto:
        return jsonify({'error': 'texto requerido'}), 400

    token = os.getenv('WHATSAPP_TOKEN', '')
    phone_id = os.getenv('PHONE_NUMBER_ID', '')
    if not token or not phone_id:
        return jsonify({'error': 'WHATSAPP_TOKEN / PHONE_NUMBER_ID no configurados en el backend'}), 500

    url = f'https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'to': chat_id,
        'type': 'text',
        'text': {'body': texto},
    }
    try:
        r = requests.post(url, headers={'Authorization': f'Bearer {token}'},
                          json=payload, timeout=15)
    except requests.RequestException as e:
        return jsonify({'error': f'error de red al enviar: {e}'}), 502
    if r.status_code >= 300:
        return jsonify({'error': 'Meta rechazó el envío', 'detalle': r.text}), 502

    usuario = get_current_identity().get('usuario', 'asesor')
    conv = _upsert_conversacion(chat_id)
    conv.modo = 'humano'
    conv.ultimo_mensaje = texto[:500]
    conv.ultima_fecha = datetime.utcnow()
    db.session.add(WaMensaje(
        chat_id=chat_id, direccion='out', texto=texto, autor=usuario,
    ))
    db.session.commit()
    return jsonify({'ok': True})
