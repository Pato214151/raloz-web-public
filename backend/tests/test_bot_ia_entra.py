"""
La IA del bot debe INTERVENIR de una cuando el cliente escribe algo natural que
las reglas no entienden (no repetir menú ni botar a asesor al primer mensaje).
"""
from app.bot.state import set_estado
from app.bot import responses


def test_ia_entra_en_primer_mensaje_raro(app, monkeypatch):
    monkeypatch.setattr(responses, 'BOT_IA_FALLBACK', True)
    monkeypatch.setattr(responses, '_respuesta_ia',
                        lambda cid, txt: responses.Respuesta('IA: claro que sí, te ayudo'))
    with app.app_context():
        set_estado('573010', 'menu')
        r = responses.construir_respuesta('573010', 'oye una cosa rara zzz', 'texto')
        assert 'IA:' in r.texto and not r.handoff


def test_sin_ia_no_pasa_a_asesor_al_primer_mensaje(app, monkeypatch):
    monkeypatch.setattr(responses, 'BOT_IA_FALLBACK', False)
    with app.app_context():
        set_estado('573011', 'menu')
        r = responses.construir_respuesta('573011', 'qwerty xyz raro', 'texto')
        # sin IA: da el menú (confuso), pero NO manda a asesor al primer intento
        assert not r.handoff
