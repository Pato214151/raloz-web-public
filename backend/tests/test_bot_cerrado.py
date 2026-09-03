"""
'Fui y estaba cerrado' → disculpa + aclara lunes/sábado + ofrece cita.
Y el horario NUNCA debe decir 'de lunes a sábado' en los mensajes fijos.
"""
from app.bot.state import set_estado
from app.bot import responses


def test_estaba_cerrado_responde_bien(app):
    with app.app_context():
        set_estado('577001', 'menu')
        r = responses.construir_respuesta('577001', 'Fui a comprar todo y estaba cerrado', 'texto')
        assert 'lunes y s' in r.texto.lower()   # aclara lunes y sábado
        assert 'cita' in r.texto.lower()          # ofrece agendar
        assert not r.handoff


def test_horario_fijo_es_lunes_y_sabado_no_rango():
    # El texto fijo del horario dice 'lunes y sábado', nunca 'lunes a sábado'.
    assert 'lunes a s' not in responses.HORARIO.lower()
    assert 'lunes y s' in responses.HORARIO.lower()
    assert '5:00' in responses.HORARIO and '6:00' not in responses.HORARIO
