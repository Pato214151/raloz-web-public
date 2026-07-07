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


def test_pago_de_saldo_por_webhook_crea_registro_pago(tienda_app):
    """El webhook de saldo debe dejar el Pago registrado (antes solo ajustaba
    los totales y la factura quedaba con total_abonado > suma de pagos)."""
    from datetime import date
    from app import db
    from app.models import Colegio, Factura, Pago, PedidoWeb
    from app.api.tienda.publico import _procesar_pago_saldo

    colegio = Colegio(nombre='Colegio T', activo=True)
    db.session.add(colegio)
    db.session.flush()
    factura = Factura(
        numero_factura='FAC-T-1', id_colegio=colegio.id_colegio,
        cliente_nombre='C', fecha_factura=date.today(),
        total=100000, total_abonado=60000, saldo_pendiente=40000,
        estado='ABONO', usuario_creacion='TIENDA_WEB',
    )
    db.session.add(factura)
    db.session.flush()
    pedido = PedidoWeb(referencia='RALOZ-TEST1', nombre_cliente='C',
                       email_cliente='c@c.co', telefono_cliente=None,
                       id_colegio=colegio.id_colegio, total=60000,
                       items_json='[]',
                       estado='pagado', id_factura=factura.id_factura)
    db.session.add(pedido)
    db.session.commit()

    with tienda_app.test_request_context():
        resp, status = _procesar_pago_saldo(
            'RALOZ-TEST1-SALDO', 'approved',
            {'id': 'pay-123', 'transaction_amount': 40000})
    assert status == 200

    factura = db.session.get(Factura, factura.id_factura)
    assert factura.saldo_pendiente == 0
    assert factura.estado == 'PAGADA'
    pago = Pago.query.filter_by(id_factura=factura.id_factura).first()
    assert pago is not None and pago.valor == 40000 and pago.usuario_registro == 'TIENDA_WEB'

    # Reintento del webhook (mismo payment_id) → idempotente, no duplica el Pago
    with tienda_app.test_request_context():
        _procesar_pago_saldo('RALOZ-TEST1-SALDO', 'approved',
                             {'id': 'pay-123', 'transaction_amount': 40000})
    assert Pago.query.filter_by(id_factura=factura.id_factura).count() == 1
