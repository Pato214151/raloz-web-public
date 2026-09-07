"""
Aviso de cierre excepcional (un lunes o sábado en que no se atiende).

Lo importante es que el aviso salga SOLO ese día y se quite solo al siguiente:
un aviso viejo colgado ("hoy no atendemos" un martes cualquiera) espanta
clientes y nadie se acuerda de borrarlo.
"""
from unittest.mock import patch

from app.bot import responses as r



def test_el_dia_del_cierre_hay_aviso():
    with patch.object(r, 'CIERRES', {'2026-09-07': 'nos surgió algo'}), \
         patch.object(r, '_cierre_hoy', lambda: 'nos surgió algo'):
        aviso = r._aviso_cierre()
    assert 'NO ATENDEMOS' in aviso
    assert 'sábado' in aviso


def test_un_dia_normal_no_hay_aviso():
    with patch.object(r, '_cierre_hoy', lambda: None):
        assert r._aviso_cierre() == ''


def test_el_aviso_encabeza_cualquier_respuesta():
    """Quien pregunta un precio también tiene que enterarse."""
    resp = r.Respuesta('🏷️ Precios de Manyanet...')
    with patch.object(r, '_cierre_hoy', lambda: 'nos surgió algo'):
        salida = r._con_aviso(resp)
    assert salida.texto.startswith('🚨')
    assert 'Precios de Manyanet' in salida.texto


def test_no_duplica_el_aviso_si_ya_lo_trae():
    resp = r.Respuesta('🚨 Hoy no atendemos...')
    with patch.object(r, '_cierre_hoy', lambda: 'nos surgió algo'):
        assert r._con_aviso(resp).texto.count('🚨') == 1
