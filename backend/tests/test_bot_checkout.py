"""
Bot de WhatsApp — el paso 'comprar_cantidad' no debe botar la venta a un asesor
cuando el cliente pregunta por disponibilidad ('¿cuántos hay?').
"""
from app.bot.state import set_estado, set_dato, get_estado
from app.bot import responses


def _prep(chat_id):
    set_estado(chat_id, 'comprar_cantidad')
    set_dato(chat_id, 'compra_colegio', 'Manyanet')
    set_dato(chat_id, 'compra_prenda', 'Blusa Niña')
    set_dato(chat_id, 'compra_talla', 'M')


def test_pregunta_disponibilidad_no_bota_a_asesor(app):
    with app.app_context():
        _prep('573001')
        r = responses.construir_respuesta('573001', '¿cuántos hay?', None)
        assert not r.handoff
        assert 'disponible' in r.texto.lower()
        assert get_estado('573001') == 'comprar_cantidad'   # sigue en el checkout


def test_texto_raro_reintenta_antes_de_asesor(app):
    with app.app_context():
        _prep('573002')
        # primer intento raro → reintenta, NO pasa a asesor
        r1 = responses.construir_respuesta('573002', 'mmm no sé', None)
        assert not r1.handoff and get_estado('573002') == 'comprar_cantidad'
        # segundo intento raro → ahora sí a asesor
        r2 = responses.construir_respuesta('573002', 'ajua', None)
        assert r2.handoff


def test_numero_valido_avanza(app):
    with app.app_context():
        _prep('573003')
        r = responses.construir_respuesta('573003', '2', None)
        assert not r.handoff
        assert get_estado('573003') == 'comprar_nombre'
