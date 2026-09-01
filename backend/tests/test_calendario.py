"""
Capacidad universal de calendario: contar días de la semana en un rango
(determinista, sin LLM). Caso real: lunes y sábados de septiembre 2026.
"""
from app.api.asistente import _tool_calendario


def test_lunes_y_sabados_septiembre_2026():
    r = _tool_calendario('2026-09-01', '2026-09-30', ['lunes', 'sabado'])
    # Septiembre 2026: sábados 5,12,19,26 (4) · lunes 7,14,21,28 (4) = 8 jornadas
    assert r['conteo'].get('sábado') == 4
    assert r['conteo'].get('lunes') == 4
    assert r['total'] == 8


def test_sin_rango_usa_mes_actual():
    r = _tool_calendario(None, None, ['domingo'])
    assert r['encontrado'] and r['total'] >= 4  # todo mes tiene 4-5 domingos
    assert r['desde'][:7] == r['hasta'][:7]     # mismo mes


def test_todos_los_dias_si_no_se_especifican():
    r = _tool_calendario('2026-09-01', '2026-09-30', None)
    assert r['total'] == 30
