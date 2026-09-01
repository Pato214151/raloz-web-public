"""
Minimización de PII (lo que se manda al modelo) + fail-closed del webhook WA.
"""
from app.api.asistente import _sin_pii


def test_sin_pii_quita_contacto_y_conserva_lo_demas():
    entrada = {
        'numero_factura': 'F1', 'cliente': 'Pedro', 'total': 45000,
        'telefono': '3001234567', 'cliente_email': 'a@b.com',
        'direccion': 'calle falsa', 'nit': '900', 'saldo': 5000,
        'detalles': [{'prenda': 'Blusa', 'telefono_cliente': '3009999999', 'cantidad': 2}],
    }
    r = _sin_pii(entrada)
    # se conserva lo útil (nombre, montos, prenda)
    assert r['cliente'] == 'Pedro' and r['total'] == 45000 and r['saldo'] == 5000
    assert r['detalles'][0]['prenda'] == 'Blusa'
    # se quita todo lo personal, también anidado
    for k in ('telefono', 'cliente_email', 'direccion', 'nit'):
        assert k not in r
    assert 'telefono_cliente' not in r['detalles'][0]


def test_webhook_wa_fail_closed_config():
    # En dev (sin RENDER) no debe exigir firma; el flag existe para prod.
    import importlib
    from app.api import whatsapp_webhook as w
    importlib.reload(w)
    assert hasattr(w, '_REQUIERE_FIRMA')
    assert hasattr(w, '_ES_PROD')
    assert w._VERIFY_DEFAULT == 'raloz-verify'
