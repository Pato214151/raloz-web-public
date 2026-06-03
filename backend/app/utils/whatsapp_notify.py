"""
Avisos al cliente por WhatsApp (vía el bot OpenWA).

El bot expone un endpoint POST /notificar. Aquí solo le pedimos que envíe
el aviso. Es "fire and forget": corre en un hilo aparte, con timeout corto y
sin lanzar errores, para NO bloquear ni romper el webhook de pago ni el panel.

Si WHATSAPP_BOT_URL no está configurado (ej. en producción todavía), esta
función simplemente no hace nada — es seguro dejarla activa.

Variables de entorno:
  WHATSAPP_BOT_URL    URL pública del bot (ej: https://bot.midominio.com)
  WHATSAPP_BOT_TOKEN  Token compartido (debe coincidir con NOTIFY_TOKEN del bot)
"""

import os
import logging
import threading

import requests

logger = logging.getLogger(__name__)


def notificar_whatsapp(telefono: str, tipo: str, datos: dict = None) -> None:
    """Pide al bot enviar un aviso al cliente. No bloquea ni lanza excepciones."""
    bot_url = os.getenv('WHATSAPP_BOT_URL', '').rstrip('/')
    bot_token = os.getenv('WHATSAPP_BOT_TOKEN', '')

    if not bot_url or not telefono:
        return  # no configurado o sin teléfono → no-op seguro

    payload = {'telefono': telefono, 'tipo': tipo, 'datos': datos or {}}

    def _enviar():
        try:
            requests.post(
                f'{bot_url}/notificar',
                json=payload,
                headers={'X-Bot-Token': bot_token},
                timeout=8,
            )
        except Exception as e:
            logger.warning('[WA] No se pudo notificar (%s): %s', tipo, e)

    threading.Thread(target=_enviar, daemon=True).start()
