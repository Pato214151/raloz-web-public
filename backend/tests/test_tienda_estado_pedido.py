"""
Tests de _estado_pedido_texto: el texto que ve el cliente (y el bot) según
el estado real del pedido. Cubre el bug del estado fantasma 'listo' (los
estados reales de PedidoFabricacion son en_produccion/listo_para_entrega/
entregado) y el puente entre los dos vocabularios de estado_entrega
(local: LISTO_EMPAQUE/LISTO_LLAMAR/ENTREGADA — web: EMPACADO/ENTREGADO).
"""
from types import SimpleNamespace

from app.api.tienda.publico import _estado_pedido_texto


def _pedido(estado='pagado'):
    return SimpleNamespace(estado=estado)


def _factura(estado_entrega):
    return SimpleNamespace(estado_entrega=estado_entrega)


def _pf(estado):
    return SimpleNamespace(estado=estado)


def test_pendiente_y_fallido():
    assert 'Pendiente' in _estado_pedido_texto(_pedido('pendiente'), None, None)
    assert 'no completado' in _estado_pedido_texto(_pedido('fallido'), None, None)


def test_fabricacion_en_produccion():
    assert 'producción' in _estado_pedido_texto(_pedido(), _factura('POR_ENTREGAR'), _pf('en_produccion'))


def test_fabricacion_listo_para_entrega():
    """Antes comparaba contra 'listo' (estado inexistente) y nunca entraba."""
    assert 'Listo para entrega' in _estado_pedido_texto(
        _pedido(), _factura('POR_ENTREGAR'), _pf('listo_para_entrega'))


def test_vocabulario_web():
    assert 'preparando' in _estado_pedido_texto(_pedido(), _factura('POR_ENTREGAR'), None)
    assert 'Empacado' in _estado_pedido_texto(_pedido(), _factura('EMPACADO'), None)
    assert 'Entregado' in _estado_pedido_texto(_pedido(), _factura('ENTREGADO'), None)


def test_vocabulario_local_tambien_mapea():
    """Facturas procesadas por el módulo de empaque local usan otros nombres."""
    assert 'Empacado' in _estado_pedido_texto(_pedido(), _factura('LISTO_LLAMAR'), None)
    assert 'Entregado' in _estado_pedido_texto(_pedido(), _factura('ENTREGADA'), None)
    assert 'preparando' in _estado_pedido_texto(_pedido(), _factura('LISTO_EMPAQUE'), None)
