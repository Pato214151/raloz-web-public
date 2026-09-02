"""
Consultas B2B / institucionales → directo a un asesor (no 'no entendí').
"""
from app.bot.state import set_estado
from app.bot import responses


def test_constructora_va_a_asesor(app):
    with app.app_context():
        set_estado('576001', 'menu')
        r = responses.construir_respuesta(
            '576001', 'La hablo por referencia de la constructora ALCABAMA', 'texto')
        assert r.handoff


def test_por_mayor_va_a_asesor(app):
    with app.app_context():
        set_estado('576002', 'menu')
        r = responses.construir_respuesta('576002', 'necesito uniformes al por mayor', 'texto')
        assert r.handoff
