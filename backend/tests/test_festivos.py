"""
Herramienta de festivos de Colombia (Nager.Date). Sin llamadas de red reales:
se mockea requests.get.
"""
from app.api import asistente as a


class _FakeResp:
    status_code = 200

    def json(self):
        return [
            {'date': '2026-01-01', 'localName': 'Año Nuevo', 'name': "New Year's Day"},
            {'date': '2026-05-01', 'localName': 'Día del Trabajo', 'name': 'Labour Day'},
        ]


def test_festivos_parsea_y_cachea(monkeypatch):
    a._FESTIVOS_CACHE.clear()
    llamadas = {'n': 0}

    def fake_get(url, timeout=8):
        llamadas['n'] += 1
        assert '/2026/CO' in url
        return _FakeResp()

    monkeypatch.setattr(a.requests, 'get', fake_get)
    r = a._tool_festivos(2026)
    assert r['encontrado'] and r['total'] == 2
    assert r['festivos'][0]['nombre'] == 'Año Nuevo'
    # segunda llamada: usa caché (no vuelve a pegarle a la API)
    a._tool_festivos(2026)
    assert llamadas['n'] == 1


def test_festivos_falla_con_gracia(monkeypatch):
    a._FESTIVOS_CACHE.clear()

    def boom(url, timeout=8):
        raise RuntimeError('sin red')

    monkeypatch.setattr(a.requests, 'get', boom)
    r = a._tool_festivos(2027)
    assert r['encontrado'] is False and 'error' in r
