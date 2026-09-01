"""
Adventista (id 2) en LIQUIDACIÓN: solo stock, precios al 50%, sin 'por encargo'.
El resto de colegios: precios normales + por encargo.
"""
from app.bot import responses

_CAT = {"productos": [
    {"id_producto": 10, "nombre": "Camisa Cuello Niño",
     "tallas": [{"talla": "M", "precio": 100000, "stock": 5}]},
    {"id_producto": 11, "nombre": "Pantalón Diario Niño",
     "tallas": [{"talla": "M", "precio": 80000, "stock": 0}]},
]}


def test_adventista_liquidacion_50_sin_encargo(monkeypatch):
    monkeypatch.setattr(responses, '_get_backend_json', lambda *a, **k: _CAT)
    texto, items = responses._consultar_precios(2, "Adventista", "M", "ambos")
    assert 'iquidaci' in texto.lower()          # banner de liquidación
    assert '50.000' in texto                     # 100.000 → 50%
    assert 'Por encargo' not in texto            # ya no se fabrica
    assert 'Pantal' not in texto                 # sin stock → no aparece
    # el item para el checkout ya lleva el precio con descuento
    assert items and items[0]['precio'] == 50000


def test_otro_colegio_precio_normal_y_encargo(monkeypatch):
    monkeypatch.setattr(responses, '_get_backend_json', lambda *a, **k: _CAT)
    texto, items = responses._consultar_precios(3, "Manyanet", "M", "ambos")
    assert '100.000' in texto                    # precio completo
    assert 'Por encargo' in texto                # sí muestra encargo
    assert items[0]['precio'] == 100000
