"""
Webhook de WhatsApp (Meta Cloud API) integrado en el BACKEND.

Antes esto vivía en un servicio aparte (whatsapp-bot/bot_meta.py) que costaba
otro plan en Render. Ahora corre DENTRO del backend que ya se paga: mismo webhook,
misma lógica (app.bot.responses), pero registrando en la bandeja EN PROCESO
(sin llamarse a sí mismo por HTTP) y con el estado de conversación en la BD.

URL del webhook en Meta:  https://raloz-web.onrender.com/api/whatsapp/webhook

Variables de entorno (en el servicio raloz-web de Render):
  WHATSAPP_TOKEN, PHONE_NUMBER_ID   → ya existen (envío desde la bandeja)
  VERIFY_TOKEN                      → la palabra secreta que pones también en Meta
  APP_SECRET                        → (recomendado) para validar la firma de Meta
  ADMIN_WHATSAPP                    → (opcional) wa_id del asesor para avisos
  GRAPH_VERSION                     → (opcional) por defecto v21.0
"""

import os
import base64
import hashlib
import hmac
import logging
from collections import deque

import requests
from flask import Blueprint, request, jsonify

from app.bot.responses import construir_respuesta
from app.api.whatsapp_inbox import registrar_mensaje_inbox

logger = logging.getLogger("raloz-wa-webhook")

wa_webhook_bp = Blueprint('wa_webhook', __name__)

GRAPH_VERSION = os.getenv('GRAPH_VERSION', 'v21.0').strip()
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'raloz-verify').strip()
APP_SECRET = os.getenv('APP_SECRET', '').strip()
ADMIN_WHATSAPP = os.getenv('ADMIN_WHATSAPP', '').strip()


def _cfg():
    """Lee token/phone_id en cada request (por si cambian sin reiniciar)."""
    return (os.getenv('WHATSAPP_TOKEN', '').strip(),
            os.getenv('PHONE_NUMBER_ID', '').strip())


def _enviar_texto(to: str, texto: str):
    token, phone_id = _cfg()
    if not (token and phone_id):
        logger.warning('Falta WHATSAPP_TOKEN o PHONE_NUMBER_ID; no se envía.')
        return
    try:
        r = requests.post(
            f'https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}/messages',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'messaging_product': 'whatsapp', 'to': to, 'type': 'text',
                  'text': {'body': texto[:4096]}},
            timeout=20,
        )
        if r.status_code >= 300:
            logger.error('Error enviando a %s: %s %s', to, r.status_code, r.text[:300])
    except Exception as e:
        logger.error('Excepción enviando a %s: %s', to, e)


def _descargar_media(media_id: str):
    token, _ = _cfg()
    if not (media_id and token):
        return None, None
    try:
        meta = requests.get(
            f'https://graph.facebook.com/{GRAPH_VERSION}/{media_id}',
            headers={'Authorization': f'Bearer {token}'}, timeout=15)
        if meta.status_code >= 300:
            return None, None
        info = meta.json()
        url = info.get('url')
        mime = info.get('mime_type', '') or 'application/octet-stream'
        if not url:
            return None, None
        binf = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=30)
        if binf.status_code >= 300 or len(binf.content) > 5_000_000:
            return None, None
        data_url = f'data:{mime};base64,{base64.b64encode(binf.content).decode()}'
        tipo = 'image' if mime.startswith('image/') else 'document'
        return data_url, tipo
    except Exception as e:
        logger.warning('No se pudo descargar media %s: %s', media_id, e)
        return None, None


# ─── Verificación del webhook (Meta hace un GET al configurarlo) ───
@wa_webhook_bp.route('/webhook', methods=['GET'])
def verificar():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info('Webhook verificado por Meta ✔')
        return challenge or '', 200
    logger.warning('Verificación fallida (token no coincide)')
    return 'forbidden', 403


def _firma_valida() -> bool:
    if not APP_SECRET:
        return True   # sin APP_SECRET no podemos validar (dev)
    header_sig = request.headers.get('X-Hub-Signature-256', '')
    if not header_sig.startswith('sha256='):
        logger.warning('Webhook sin firma válida (rechazado)')
        return False
    try:
        esperado = hmac.new(APP_SECRET.encode('utf-8'),
                            request.get_data(cache=True) or b'', hashlib.sha256).hexdigest()
    except Exception as e:
        logger.error('Error calculando HMAC: %s', e)
        return False
    return hmac.compare_digest(esperado, header_sig.split('=', 1)[1])


# Anti-duplicados (Meta reintenta si tardamos en responder)
_VISTOS = deque(maxlen=500)


def _es_duplicado(mid: str) -> bool:
    if not mid:
        return False
    if mid in _VISTOS:
        return True
    _VISTOS.append(mid)
    return False


@wa_webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    if not _firma_valida():
        return jsonify({'error': 'invalid_signature'}), 401
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                contactos = value.get('contacts', [])
                nombre = (contactos[0].get('profile') or {}).get('name') if contactos else None
                for msg in value.get('messages', []):
                    if _es_duplicado(msg.get('id')):
                        continue
                    _procesar_mensaje(msg, nombre)
    except Exception as e:
        logger.error('Error procesando webhook: %s', e)
    return jsonify({'status': 'ok'}), 200


def _procesar_mensaje(msg: dict, nombre: str = None):
    numero = msg.get('from')
    tipo = msg.get('type', 'text')
    if not numero:
        return

    media_id = None
    if tipo == 'text':
        texto = (msg.get('text') or {}).get('body', '')
        contenido = 'texto'
    elif tipo == 'interactive':
        inter = msg.get('interactive', {})
        br = inter.get('button_reply') or inter.get('list_reply') or {}
        texto = br.get('title') or br.get('id') or ''
        contenido = 'texto'
    elif tipo == 'image':
        img = msg.get('image') or {}
        texto = img.get('caption', '') or '📷 Imagen'
        media_id = img.get('id')
        contenido = 'foto'
    elif tipo == 'document':
        doc = msg.get('document') or {}
        texto = doc.get('caption') or doc.get('filename') or '📎 Archivo'
        media_id = doc.get('id')
        contenido = 'otro'
    else:
        texto = ''
        contenido = 'otro'

    media_b64, media_tipo = (_descargar_media(media_id) if media_id else (None, None))

    # Registrar entrante EN PROCESO (sin auto-HTTP) y ver quién atiende
    modo = registrar_mensaje_inbox(numero, 'in', texto, nombre=nombre, autor='cliente',
                                   media_b64=media_b64, media_tipo=media_tipo)

    if modo == 'humano':
        logger.info('Chat %s en modo humano; el bot no responde.', numero)
        return

    resp = construir_respuesta(numero, texto, contenido)
    nuevo_modo = 'humano' if getattr(resp, 'handoff', False) else None
    if resp.texto:
        _enviar_texto(numero, resp.texto)
        registrar_mensaje_inbox(numero, 'out', resp.texto, nombre=nombre, autor='bot',
                                set_modo=nuevo_modo)
    if resp.aviso_admin and ADMIN_WHATSAPP:
        _enviar_texto(ADMIN_WHATSAPP, resp.aviso_admin)
