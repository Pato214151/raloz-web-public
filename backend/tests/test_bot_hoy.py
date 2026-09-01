"""
'¿Atienden hoy? / ¿puedo pasar hoy?' → respuesta DIRECTA según el día,
no el horario genérico ni 'no entendí'.
"""
from app.bot.state import set_estado
from app.bot import responses


def test_puedo_pasar_hoy_responde_directo(app):
    with app.app_context():
        set_estado('574001', 'menu')
        r = responses.construir_respuesta('574001', '¿puedo pasar hoy?', 'texto')
        assert '5:00 p.m.' in r.texto            # da la info del día, no 'no entendí'
        assert not r.handoff


def test_estan_atendiendo_hoy(app):
    with app.app_context():
        set_estado('574002', 'menu')
        r = responses.construir_respuesta('574002', 'Hoy están atendiendo?', 'texto')
        assert '5:00 p.m.' in r.texto


def test_saludo_sigue_dando_menu(app):
    with app.app_context():
        set_estado('574003', 'menu')
        r = responses.construir_respuesta('574003', 'buenos días', 'texto')
        # un saludo normal NO debe caer en el handler de 'hoy'
        assert '5:00 p.m.' not in r.texto
