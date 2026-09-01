"""
Herramienta: chats de WhatsApp sin responder (para que RALOZ los avise).
"""
from datetime import datetime, timedelta

from app import db
from app.models import WaConversacion
from app.api.asistente import _tool_whatsapp_pendientes


def test_lista_solo_chats_con_no_leidos_sin_exponer_telefono(app):
    with app.app_context():
        db.session.add(WaConversacion(chat_id='573001112233', nombre='María',
                                      ultimo_mensaje='hola, ¿tienen talla 10?',
                                      no_leidos=2, modo='bot',
                                      ultima_fecha=datetime.utcnow() - timedelta(hours=3)))
        db.session.add(WaConversacion(chat_id='573004445566', nombre='Ya leído',
                                      ultimo_mensaje='listo', no_leidos=0))
        db.session.commit()
        r = _tool_whatsapp_pendientes(15)
        assert r['total_chats'] == 1 and r['total_sin_leer'] == 2
        chat = r['chats'][0]
        assert chat['nombre'] == 'María' and chat['no_leidos'] == 2
        assert chat['hace_horas'] is not None
        # nunca se expone el teléfono/chat_id
        assert 'chat_id' not in chat and 'telefono' not in chat


def test_sin_pendientes_devuelve_vacio(app):
    with app.app_context():
        db.session.add(WaConversacion(chat_id='57300', nombre='x', no_leidos=0))
        db.session.commit()
        r = _tool_whatsapp_pendientes(15)
        assert r['encontrado'] is False and r['total_chats'] == 0
