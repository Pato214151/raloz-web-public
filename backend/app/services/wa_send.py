"""
Envío de mensajes de WhatsApp desde el backend (Cloud API de Meta).
Reutilizable por citas, notificaciones, etc. Registra el mensaje en la bandeja.
"""

import os
from datetime import datetime

import requests

from app import db
from app.models import WaConversacion, WaMensaje

GRAPH_VERSION = os.getenv('GRAPH_VERSION', 'v21.0')


def enviar_whatsapp(to: str, texto: str, autor: str = 'sistema', registrar: bool = True) -> bool:
    """Envía un texto por la Cloud API. Devuelve True si se envió.
    Si registrar=True, además lo deja en la bandeja del panel."""
    token = os.getenv('WHATSAPP_TOKEN', '')
    phone_id = os.getenv('PHONE_NUMBER_ID', '')
    to = ''.join(ch for ch in (to or '') if ch.isdigit())
    if not token or not phone_id or not to:
        return False

    url = f'https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}/messages'
    try:
        r = requests.post(
            url, headers={'Authorization': f'Bearer {token}'},
            json={'messaging_product': 'whatsapp', 'to': to, 'type': 'text',
                  'text': {'body': texto[:4096]}},
            timeout=15,
        )
    except requests.RequestException:
        return False
    if r.status_code >= 300:
        return False

    if registrar:
        try:
            conv = db.session.get(WaConversacion, to)
            if conv is None:
                conv = WaConversacion(chat_id=to, modo='bot')
                db.session.add(conv)
            conv.ultimo_mensaje = texto[:500]
            conv.ultima_fecha = datetime.utcnow()
            db.session.add(WaMensaje(chat_id=to, direccion='out', texto=texto, autor=autor))
            db.session.commit()
        except Exception:
            db.session.rollback()
    return True
