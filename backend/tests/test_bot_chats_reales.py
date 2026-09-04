"""
Fallas vistas en chats reales de WhatsApp (1 y 2 de septiembre de 2026).

Cada test reproduce un mensaje que un cliente escribió de verdad y con el que
el bot falló: se rindió, dio información errada o se quedó en bucle.
"""
from app.bot.responses import (
    _detectar_colegio, _detectar_talla, _norm, _habla_de_horario,
)


def test_colegio_mal_escrito_se_entiende():
    """"Mayanet" (sin la n) dejó al cliente en bucle hasta que pidió asesor."""
    assert _detectar_colegio(_norm('Mayanet')) == (3, 'Manyanet')
    assert _detectar_colegio(_norm('marilac')) == (1, 'Marillac')
    assert _detectar_colegio(_norm('adbentista')) == (2, 'Adventista')


def test_palabra_cualquiera_no_es_un_colegio():
    assert _detectar_colegio(_norm('hola buenas tardes')) == (None, None)


def test_direccion_no_se_lee_como_talla():
    """El bot tomó el 68 de "San Andresito de la 68" y dijo que no existía."""
    assert _detectar_talla(_norm('CC San Andresito de la 68, Local M14 (2 piso)')) is None


def test_numero_que_no_es_talla_se_descarta():
    assert _detectar_talla(_norm('68')) is None


def test_tallas_de_verdad_siguen_funcionando():
    assert _detectar_talla(_norm('M')) == 'M'
    assert _detectar_talla(_norm('12')) == '12'
    assert _detectar_talla(_norm('10-12')) == '10-12'
    assert _detectar_talla(_norm('necesito la talla 14 por favor')) == '14'


def test_horario_inventado_por_la_ia_se_bloquea():
    """La IA dijo "de lunes a sábado" y una clienta viajó un día cerrado."""
    assert _habla_de_horario('Atendemos de lunes a sábado de 10 a 5')
    assert _habla_de_horario('Estamos abiertos todos los días')
    assert not _habla_de_horario('Claro, con gusto te ayudo con la blusa')
