"""
Tests de validadores de entrada — protegen contra datos inválidos/maliciosos.
"""
from app.utils.validators import (
    sanitize_string,
    validate_email,
    validate_phone,
    validate_date,
    validate_positive_number,
    validate_required_fields,
)


def test_sanitize_string_quita_html():
    assert sanitize_string("<script>alert(1)</script>hola") == "alert(1)hola"
    assert sanitize_string("<b>texto</b>") == "texto"


def test_sanitize_string_trunca_y_maneja_vacio():
    assert sanitize_string("a" * 600, max_length=10) == "a" * 10
    assert sanitize_string("") == ""
    assert sanitize_string(None) is None


def test_validate_email():
    assert validate_email("cliente@correo.com") is True
    assert validate_email("ralozcol@outlook.com") is True
    assert validate_email("sin-arroba.com") is False
    assert validate_email("a@b") is False
    assert validate_email("") is False


def test_validate_phone():
    assert validate_phone("3213412903") is True
    assert validate_phone("+57 321 341 2903") is True
    assert validate_phone("") is True          # opcional
    assert validate_phone("123") is False      # muy corto
    assert validate_phone("abcde123") is False


def test_validate_date():
    assert validate_date("2026-06-15") is not None
    assert validate_date("15/06/2026") is None  # formato distinto
    assert validate_date("no-es-fecha") is None
    assert validate_date(None) is None


def test_validate_positive_number():
    assert validate_positive_number(10) is True
    assert validate_positive_number("56000") is True
    assert validate_positive_number(0) is False
    assert validate_positive_number(-5) is False
    assert validate_positive_number("abc") is False


def test_validate_required_fields():
    ok, _ = validate_required_fields({"nombre": "Ana", "tel": "3001"}, ["nombre", "tel"])
    assert ok is True
    falla, msg = validate_required_fields({"nombre": "Ana"}, ["nombre", "tel"])
    assert falla is False
    assert "tel" in msg
