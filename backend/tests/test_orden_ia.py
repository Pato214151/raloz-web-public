"""
Orden de proveedores de IA (IA_PRINCIPAL). Por defecto Gemini primero.
"""
import os
from app.api.asistente import _orden_ia


def test_por_defecto_gemini_primero(monkeypatch):
    monkeypatch.delenv('IA_PRINCIPAL', raising=False)
    orden = _orden_ia()
    assert orden[0] == 'gemini'
    assert set(orden) == {'gemini', 'groq', 'grok', 'deepseek'}


def test_principal_configurable(monkeypatch):
    monkeypatch.setenv('IA_PRINCIPAL', 'groq')
    orden = _orden_ia()
    assert orden[0] == 'groq'
    assert set(orden) == {'gemini', 'groq', 'grok', 'deepseek'}  # los otros siguen de respaldo
