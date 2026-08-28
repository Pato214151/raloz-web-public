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
import re
import csv
import io
import json
import base64
from datetime import datetime, timedelta

import requests
from flask import Blueprint, request, jsonify, Response

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


# ─────────────────────── Registro de mensajes (reutilizable) ───────────
def registrar_mensaje_inbox(chat_id, direccion, texto='', nombre=None, autor=None,
                            set_modo=None, media_tipo=None, media_b64=None):
    """Guarda un mensaje en la bandeja y devuelve el modo actual del chat
    ('bot' | 'humano'). Se usa tanto desde el endpoint /log (bot externo) como
    desde el webhook de WhatsApp integrado en el backend — así el bot integrado
    NO tiene que llamarse a sí mismo por HTTP."""
    autor = autor or ('cliente' if direccion == 'in' else 'bot')
    conv = _upsert_conversacion(chat_id, nombre)
    conv.ultimo_mensaje = (texto or '')[:500]
    conv.ultima_fecha = datetime.utcnow()
    if direccion == 'in':
        conv.no_leidos = (conv.no_leidos or 0) + 1
    if set_modo in ('bot', 'humano'):
        conv.modo = set_modo

    db.session.add(WaMensaje(
        chat_id=chat_id, direccion=direccion, texto=texto, autor=autor,
        media_tipo=media_tipo, media_b64=media_b64,
    ))
    db.session.commit()

    # Notificación push al panel cuando escribe un cliente (best-effort)
    if direccion == 'in':
        try:
            from app.api.push import enviar_push_a_todos
            nombre_cli = conv.nombre or chat_id
            preview = (texto or '📎 Adjunto')[:120]
            enviar_push_a_todos(f'💬 {nombre_cli}', preview, url='/whatsapp')
        except Exception:
            pass

    return conv.modo or 'bot'


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

    if not chat_id or direccion not in ('in', 'out'):
        return jsonify({'error': 'chat_id y direccion (in|out) requeridos'}), 400

    modo = registrar_mensaje_inbox(
        chat_id, direccion,
        texto=data.get('texto') or '',
        nombre=data.get('nombre'),
        autor=data.get('autor'),
        set_modo=data.get('set_modo'),
        media_tipo=data.get('media_tipo'),
        media_b64=data.get('media_b64'),
    )
    return jsonify({'ok': True, 'modo': modo})


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
             # Los chats del asistente web (prefijo 'web:') no van en la bandeja de WhatsApp
             .filter(~WaConversacion.chat_id.like('web:%'))
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


@wa_inbox_bp.route('/conversaciones/<chat_id>/mensajes/<int:id_mensaje>', methods=['DELETE'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def eliminar_mensaje(chat_id, id_mensaje):
    """Borra un mensaje de la BANDEJA (solo del panel). OJO: no lo elimina del
    WhatsApp del cliente — la Cloud API de Meta no permite borrar/editar mensajes
    ya enviados. Sirve para limpiar el historial interno."""
    msg = db.session.get(WaMensaje, id_mensaje)
    if not msg or msg.chat_id != chat_id:
        return jsonify({'error': 'mensaje no encontrado'}), 404
    db.session.delete(msg)
    db.session.commit()
    return jsonify({'ok': True})


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


@wa_inbox_bp.route('/conversaciones/<chat_id>/asignar', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def asignar_conversacion(chat_id):
    """Asigna la conversación a un asesor (o la deja sin asignar con null/''.)."""
    data = request.get_json(silent=True) or {}
    asignado = (data.get('asignado_a') or '').strip() or None
    conv = _upsert_conversacion(chat_id)
    conv.asignado_a = asignado
    # Al asignar a una persona, el chat pasa a modo humano (el bot se calla).
    if asignado:
        conv.modo = 'humano'
    db.session.commit()
    return jsonify({'ok': True, 'asignado_a': conv.asignado_a, 'modo': conv.modo})


@wa_inbox_bp.route('/conversaciones/<chat_id>/etiquetas', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def etiquetas_conversacion(chat_id):
    """Reemplaza la lista de etiquetas de la conversación."""
    data = request.get_json(silent=True) or {}
    etiquetas = data.get('etiquetas')
    if not isinstance(etiquetas, list):
        return jsonify({'error': 'etiquetas debe ser una lista'}), 400
    # Limpiar, recortar y quitar duplicados/ vacíos (máx 12, 30 chars c/u)
    limpias = []
    for e in etiquetas:
        s = str(e).strip()[:30]
        if s and s not in limpias:
            limpias.append(s)
        if len(limpias) >= 12:
            break
    conv = _upsert_conversacion(chat_id)
    conv.etiquetas = json.dumps(limpias, ensure_ascii=False)
    db.session.commit()
    return jsonify({'ok': True, 'etiquetas': limpias})


@wa_inbox_bp.route('/conversaciones/<chat_id>/notas', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def notas_conversacion(chat_id):
    """Guarda las notas internas de la conversación."""
    data = request.get_json(silent=True) or {}
    notas = (data.get('notas') or '')[:4000]
    conv = _upsert_conversacion(chat_id)
    conv.notas = notas
    db.session.commit()
    return jsonify({'ok': True, 'notas': conv.notas})


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


@wa_inbox_bp.route('/conversaciones/<chat_id>/enviar-imagen', methods=['POST'])
@rol_requerido('administrador', 'vendedor', 'cajero')
def enviar_imagen(chat_id):
    """Un asesor envía una imagen desde el panel: se sube a Meta y se manda."""
    data = request.get_json(silent=True) or {}
    m = re.match(r'data:([^;]+);base64,(.*)', data.get('imagen_b64') or '', re.DOTALL)
    if not m:
        return jsonify({'error': 'imagen inválida'}), 400
    mime, b64 = m.group(1), m.group(2)
    caption = (data.get('caption') or '').strip()
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return jsonify({'error': 'base64 inválido'}), 400
    if len(raw) > 5_000_000:
        return jsonify({'error': 'imagen muy grande (máx 5 MB)'}), 400

    token = os.getenv('WHATSAPP_TOKEN', '')
    phone_id = os.getenv('PHONE_NUMBER_ID', '')
    if not token or not phone_id:
        return jsonify({'error': 'WHATSAPP_TOKEN / PHONE_NUMBER_ID no configurados'}), 500
    base = f'https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}'

    # 1) subir la imagen a Meta → media_id
    try:
        up = requests.post(
            f'{base}/media', headers={'Authorization': f'Bearer {token}'},
            files={'file': ('foto', raw, mime)},
            data={'messaging_product': 'whatsapp', 'type': mime}, timeout=30)
    except requests.RequestException as e:
        return jsonify({'error': f'error subiendo: {e}'}), 502
    if up.status_code >= 300:
        return jsonify({'error': 'Meta rechazó la subida', 'detalle': up.text}), 502
    media_id = (up.json() or {}).get('id')
    if not media_id:
        return jsonify({'error': 'sin media_id'}), 502

    # 2) enviar el mensaje de imagen
    img = {'id': media_id}
    if caption:
        img['caption'] = caption
    try:
        snd = requests.post(
            f'{base}/messages', headers={'Authorization': f'Bearer {token}'},
            json={'messaging_product': 'whatsapp', 'to': chat_id, 'type': 'image', 'image': img},
            timeout=20)
    except requests.RequestException as e:
        return jsonify({'error': f'error enviando: {e}'}), 502
    if snd.status_code >= 300:
        return jsonify({'error': 'Meta rechazó el envío', 'detalle': snd.text}), 502

    # 3) registrar en la bandeja
    usuario = get_current_identity().get('usuario', 'asesor')
    conv = _upsert_conversacion(chat_id)
    conv.modo = 'humano'
    conv.ultimo_mensaje = caption or '📷 Imagen'
    conv.ultima_fecha = datetime.utcnow()
    db.session.add(WaMensaje(
        chat_id=chat_id, direccion='out', texto=caption or '', autor=usuario,
        media_tipo='image', media_b64=data.get('imagen_b64'),
    ))
    db.session.commit()
    return jsonify({'ok': True})


def generar_csv_whatsapp():
    """Arma un CSV (texto) con todas las conversaciones y mensajes, hora de Bogotá.
    No incluye las imágenes en sí (solo marca si el mensaje traía adjunto)."""
    nombres = {c.chat_id: (c.nombre or '') for c in WaConversacion.query.all()}

    buf = io.StringIO()
    buf.write('﻿')   # BOM para que Excel muestre bien tildes y ñ
    w = csv.writer(buf)
    w.writerow(['Fecha (Bogotá)', 'Teléfono', 'Nombre', 'Dirección', 'Autor', 'Mensaje', 'Adjunto'])

    for m in WaMensaje.query.order_by(WaMensaje.chat_id, WaMensaje.fecha).all():
        # Bogotá = UTC-5 (sin horario de verano)
        fecha_bog = (m.fecha - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M') if m.fecha else ''
        direccion = 'Entrante' if m.direccion == 'in' else 'Saliente'
        w.writerow([
            fecha_bog, m.chat_id, nombres.get(m.chat_id, ''),
            direccion, m.autor or '', m.texto or '', getattr(m, 'media_tipo', None) or '',
        ])
    return buf.getvalue()


@wa_inbox_bp.route('/exportar', methods=['GET'])
@rol_requerido('administrador', 'vendedor')
def exportar_conversaciones():
    """Descarga TODAS las conversaciones y mensajes de WhatsApp en un CSV
    (compatible con Excel, hora de Bogotá)."""
    nombre_archivo = f"whatsapp_raloz_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        generar_csv_whatsapp(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{nombre_archivo}"'},
    )
