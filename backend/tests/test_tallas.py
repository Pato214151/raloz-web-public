"""
Tests de conversión de tallas — ruta crítica: de aquí dependen los precios
(por grupo de talla) y el stock (por talla individual). Un error aquí afecta
cuánto se cobra y qué inventario se descuenta.
"""
import pytest

from app.utils.tallas import (
    convertir_a_grupo,
    convertir_a_individuales,
    validar_talla_individual,
    validar_talla_grupo,
    TALLA_INDIVIDUAL_A_GRUPO,
    TALLA_GRUPO_A_INDIVIDUALES,
)


@pytest.mark.parametrize("individual,grupo", [
    ("4", "4"),
    ("6", "6-8"),
    ("8", "6-8"),
    ("10", "10-12"),
    ("12", "10-12"),
    ("14", "14-16"),
    ("16", "14-16"),
    ("S", "S-M"),
    ("M", "S-M"),
    ("L", "L"),
    ("XL", "XL"),
])
def test_convertir_a_grupo(individual, grupo):
    assert convertir_a_grupo(individual) == grupo


def test_convertir_a_grupo_invalida():
    with pytest.raises(ValueError):
        convertir_a_grupo("99")


@pytest.mark.parametrize("grupo,individuales", [
    ("4", ["4"]),
    ("6-8", ["6", "8"]),
    ("10-12", ["10", "12"]),
    ("14-16", ["14", "16"]),
    ("S-M", ["S", "M"]),
    ("L", ["L"]),
    ("XL", ["XL"]),
])
def test_convertir_a_individuales(grupo, individuales):
    assert convertir_a_individuales(grupo) == individuales


def test_convertir_a_individuales_invalida():
    with pytest.raises(ValueError):
        convertir_a_individuales("ZZ")


def test_ida_y_vuelta_es_consistente():
    """Cada talla individual, convertida a grupo y de vuelta, se incluye a sí misma."""
    for individual in TALLA_INDIVIDUAL_A_GRUPO:
        grupo = convertir_a_grupo(individual)
        assert individual in convertir_a_individuales(grupo)


def test_todos_los_grupos_mapean_de_vuelta():
    """Cada talla individual de un grupo pertenece efectivamente a ese grupo."""
    for grupo, individuales in TALLA_GRUPO_A_INDIVIDUALES.items():
        for ind in individuales:
            assert convertir_a_grupo(ind) == grupo


def test_validadores():
    assert validar_talla_individual("6") is True
    assert validar_talla_individual("99") is False
    assert validar_talla_grupo("6-8") is True
    assert validar_talla_grupo("6") is False  # "6" es individual, no grupo
