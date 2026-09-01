"""
Flujo de domicilio: muestra estimado por zona, captura la dirección y avisa al
asesor para el valor exacto (que se coordina por app).
"""
from app.bot.state import set_estado
from app.bot import responses


def test_intent_domicilio_muestra_rangos_y_pide_direccion(app):
    with app.app_context():
        set_estado('575001', 'menu')
        r = responses.construir_respuesta('575001', '¿hacen domicilios?', 'texto')
        assert '8.000' in r.texto and '12.000' in r.texto     # muestra los rangos
        from app.bot.state import get_estado
        assert get_estado('575001') == 'entrega_direccion'    # queda esperando la dirección


def test_direccion_con_colegio_da_estimado_y_avisa(app):
    with app.app_context():
        set_estado('575002', 'entrega_direccion')
        r = responses.construir_respuesta(
            '575002', 'Carrera 108 #70f-17, barrio, colegio Manyanet', 'texto')
        assert r.handoff                       # pasa al asesor con la dirección
        assert '8.000' in r.texto              # estimado de la zona Manyanet
        assert 'Carrera 108' in r.texto        # confirmó la dirección (no la pierde)


def test_direccion_sin_colegio_igual_registra(app):
    with app.app_context():
        set_estado('575003', 'entrega_direccion')
        r = responses.construir_respuesta('575003', 'Calle 45 # 12-30', 'texto')
        assert r.handoff and 'Calle 45' in r.texto
