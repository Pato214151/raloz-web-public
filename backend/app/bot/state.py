"""
Estado de la conversación del bot — versión en BASE DE DATOS.

Reemplaza el state.py en memoria del bot antiguo. Antes el estado vivía en un
dict del proceso, lo que obligaba a correr el bot con UN solo worker. Ahora que
el bot corre DENTRO del backend (con 2 workers de gunicorn), el estado se guarda
en la fila de WaConversacion (columnas bot_estado y bot_datos), así cualquier
worker ve el mismo estado.

Mantiene la MISMA interfaz que usaba responses.py:
  get_estado, set_estado, reset_estado, set_dato, get_dato

Se llama siempre dentro del contexto de una request (el webhook), así que
db.session está disponible. Los datos temporales van en bot_datos como JSON.
"""

import json
import logging

from app import db
from app.models import WaConversacion

logger = logging.getLogger("raloz-bot.state")


def _conv(chat_id: str, crear: bool = False):
    conv = db.session.get(WaConversacion, chat_id)
    if conv is None and crear:
        conv = WaConversacion(chat_id=chat_id, modo='bot', bot_estado='menu')
        db.session.add(conv)
    return conv


def get_estado(chat_id: str) -> str:
    conv = _conv(chat_id)
    return (conv.bot_estado if conv and conv.bot_estado else 'menu')


def set_estado(chat_id: str, estado: str) -> None:
    conv = _conv(chat_id, crear=True)
    conv.bot_estado = estado
    db.session.commit()


def reset_estado(chat_id: str) -> None:
    conv = _conv(chat_id)
    if conv is not None:
        conv.bot_estado = 'menu'
        conv.bot_datos = None
        db.session.commit()


def set_dato(chat_id: str, clave: str, valor) -> None:
    conv = _conv(chat_id, crear=True)
    try:
        datos = json.loads(conv.bot_datos) if conv.bot_datos else {}
    except Exception:
        datos = {}
    datos[clave] = valor
    conv.bot_datos = json.dumps(datos, ensure_ascii=False)
    db.session.commit()


def get_dato(chat_id: str, clave: str, default=None):
    conv = _conv(chat_id)
    if not conv or not conv.bot_datos:
        return default
    try:
        return json.loads(conv.bot_datos).get(clave, default)
    except Exception:
        return default
