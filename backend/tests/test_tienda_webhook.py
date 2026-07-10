"""
Tests del flujo crítico de pago: webhook de MercadoPago → factura → stock.

Se mockea la consulta a la API de MercadoPago (requests.get) y el envío
de email. WhatsApp es no-op porque WHATSAPP_BOT_URL no está configurado.
"""
import json
import pytest
from datetime import date
from app import db
from app.models import (
    Colegio, Producto, Stock, Reserva, PedidoWeb, Factura,
    Pago, PedidoFabricacion, StockPendienteFabricacion,
)
from app.api.tienda import publico as tienda


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture
def entorno_mp(monkeypatch):
    """Configura el entorno para que el webhook procese pagos sin servicios externos."""
    monkeypatch.setenv('MP_ACCESS_TOKEN', 'test-token')
    monkeypatch.delenv('MP_WEBHOOK_SECRET', raising=False)   # sin firma → validación omitida
    monkeypatch.delenv('WHATSAPP_BOT_URL', raising=False)    # whatsapp → no-op
    monkeypatch.delenv('ADMIN_WHATSAPP', raising=False)
    # No lanzar hilos de email en tests
    monkeypatch.setattr(tienda, '_lanzar_email_async', lambda *a, **k: None)


def _mock_pago_mp(monkeypatch, referencia, estado='approved', monto=50000):
    """Hace que la consulta a MP devuelva un pago con ese estado y referencia."""
    def fake_get(url, **kwargs):
        return _FakeResponse({
            'id': 999,
            'status': estado,
            'external_reference': referencia,
            'payment_type_id': 'credit_card',
            'transaction_amount': monto,
        })
    monkeypatch.setattr(tienda.requests, 'get', fake_get)


def _crear_escenario(stock_inicial=5, cantidad=2, con_reserva=True, tipo_pedido='normal'):
    """Colegio + producto + stock + pedido web pendiente (como lo deja /pedido)."""
    colegio = Colegio(nombre='COLEGIO TEST', ciudad='Bogotá')
    producto = Producto(nombre='Camisa Test', tipo='camisa')
    db.session.add_all([colegio, producto])
    db.session.flush()

    db.session.add(Stock(
        id_colegio=colegio.id_colegio, id_producto=producto.id_producto,
        talla_individual='8', cantidad=stock_inicial,
    ))

    id_reserva = None
    if con_reserva:
        from datetime import date, datetime, timedelta
        reserva = Reserva(
            session_id='sesion-test', id_colegio=colegio.id_colegio,
            id_producto=producto.id_producto, talla='8', cantidad=cantidad,
            fecha_expiracion=datetime.utcnow() + timedelta(minutes=30),
        )
        db.session.add(reserva)
        db.session.flush()
        id_reserva = reserva.id_reserva

    precio = 25000
    item = {
        'id_producto': producto.id_producto,
        'nombre': 'Camisa Test',
        'talla': '8',
        'cantidad': cantidad,
        'precio_unitario': precio,
        'subtotal': precio * cantidad,
        'id_reserva': id_reserva,
        'tipo_pedido': tipo_pedido,
        'stock_disponible': cantidad if tipo_pedido == 'normal' else 0,
    }
    pedido = PedidoWeb(
        referencia='RALOZ-TEST0001',
        nombre_cliente='Cliente Prueba',
        email_cliente='cliente@test.com',
        telefono_cliente='3001234567',
        id_colegio=colegio.id_colegio,
        nombre_colegio=colegio.nombre,
        items_json=json.dumps([item]),
        total=precio * cantidad,
        total_orden=precio * cantidad,
        abono_porcentaje=100,
        tiene_fabricacion=(tipo_pedido != 'normal'),
        estado='pendiente',
    )
    db.session.add(pedido)
    db.session.commit()
    return colegio, producto, pedido, id_reserva


def _webhook(client):
    return client.post('/api/tienda/mp/webhook', json={
        'type': 'payment',
        'data': {'id': '999'},
    })


def test_pago_aprobado_crea_factura_y_descuenta_stock(tienda_client, entorno_mp, monkeypatch):
    colegio, producto, pedido, id_reserva = _crear_escenario(stock_inicial=5, cantidad=2)
    _mock_pago_mp(monkeypatch, pedido.referencia)

    resp = _webhook(tienda_client)
    assert resp.status_code == 200

    db.session.refresh(pedido)
    assert pedido.estado == 'pagado'
    assert pedido.id_factura is not None

    factura = db.session.get(Factura, pedido.id_factura)
    assert factura.estado == 'PAGADA'
    assert factura.total == 50000
    assert factura.saldo_pendiente == 0

    stock = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == 3  # 5 - 2

    assert db.session.get(Reserva, id_reserva).estado == 'completada'
    assert Pago.query.filter_by(id_factura=factura.id_factura).count() == 1


def test_webhook_reintentado_es_idempotente(tienda_client, entorno_mp, monkeypatch):
    """MP reintenta el webhook: NO debe crear otra factura ni descontar stock dos veces."""
    colegio, producto, pedido, _ = _crear_escenario(stock_inicial=5, cantidad=2)
    _mock_pago_mp(monkeypatch, pedido.referencia)

    assert _webhook(tienda_client).status_code == 200
    assert _webhook(tienda_client).status_code == 200  # reintento

    assert Factura.query.count() == 1
    stock = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == 3  # descontado UNA sola vez


def test_pago_rechazado_libera_reserva(tienda_client, entorno_mp, monkeypatch):
    colegio, producto, pedido, id_reserva = _crear_escenario(stock_inicial=5, cantidad=2)
    _mock_pago_mp(monkeypatch, pedido.referencia, estado='rejected')

    assert _webhook(tienda_client).status_code == 200

    db.session.refresh(pedido)
    assert pedido.estado == 'fallido'
    assert pedido.id_factura is None
    assert db.session.get(Reserva, id_reserva).estado == 'cancelada'
    stock = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == 5  # intacto


def test_race_de_stock_reclasifica_a_fabricacion(tienda_client, entorno_mp, monkeypatch):
    """Si el stock real bajó entre el pedido y el pago, la diferencia va a fabricación."""
    colegio, producto, pedido, _ = _crear_escenario(stock_inicial=1, cantidad=2, con_reserva=False)
    _mock_pago_mp(monkeypatch, pedido.referencia)

    assert _webhook(tienda_client).status_code == 200

    stock = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == 0  # descontó solo lo que había

    db.session.refresh(pedido)
    items = json.loads(pedido.items_json)
    assert items[0]['tipo_pedido'] == 'mixto'
    assert items[0]['stock_disponible'] == 1

    pf = PedidoFabricacion.query.filter_by(id_pedido_web=pedido.id_pedido).first()
    assert pf is not None
    spf = StockPendienteFabricacion.query.filter_by(id_producto=producto.id_producto, talla='8').first()
    assert spf is not None
    assert spf.cantidad_pendiente == 1  # la unidad faltante


def _facturar(tienda_client, entorno_mp, monkeypatch, escenario):
    """Procesa el pago aprobado para dejar el pedido con factura y stock descontado."""
    colegio, producto, pedido, id_reserva = escenario
    _mock_pago_mp(monkeypatch, pedido.referencia, estado='approved')
    assert _webhook(tienda_client).status_code == 200
    db.session.refresh(pedido)
    assert pedido.id_factura is not None
    return colegio, producto, pedido, id_reserva


def test_reembolso_de_pedido_facturado_avisa_y_no_toca_stock(tienda_client, entorno_mp, monkeypatch):
    """
    Reembolso de una venta ya facturada: avisa al admin, NO devuelve stock ni
    anula la factura (la prenda física puede no haber vuelto). Marca 'reembolsado'.
    """
    from app.api.tienda import publico as tienda
    avisos = []
    monkeypatch.setattr(tienda, '_avisar_admin', lambda texto: avisos.append(texto))

    colegio, producto, pedido, _ = _facturar(
        tienda_client, entorno_mp, monkeypatch, _crear_escenario(stock_inicial=5, cantidad=2))
    stock_tras_pago = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first().cantidad
    assert stock_tras_pago == 3  # 5 - 2 descontado por la venta

    _mock_pago_mp(monkeypatch, pedido.referencia, estado='refunded')
    assert _webhook(tienda_client).status_code == 200

    db.session.refresh(pedido)
    assert pedido.estado == 'reembolsado'
    # Factura intacta (anulación es manual cuando vuelve la prenda)
    factura = db.session.get(Factura, pedido.id_factura)
    assert factura.estado == 'PAGADA'
    # Stock NO cambió por el reembolso
    stock = Stock.query.filter_by(id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == 3
    # Sí avisó al admin
    assert len(avisos) == 1
    assert pedido.referencia in avisos[0]


def test_reembolso_repetido_no_avisa_dos_veces(tienda_client, entorno_mp, monkeypatch):
    """MP reintenta el webhook de reembolso: el admin debe recibir UN solo aviso."""
    from app.api.tienda import publico as tienda
    avisos = []
    monkeypatch.setattr(tienda, '_avisar_admin', lambda texto: avisos.append(texto))

    _, _, pedido, _ = _facturar(
        tienda_client, entorno_mp, monkeypatch, _crear_escenario(stock_inicial=5, cantidad=2))

    _mock_pago_mp(monkeypatch, pedido.referencia, estado='refunded')
    assert _webhook(tienda_client).status_code == 200
    assert _webhook(tienda_client).status_code == 200  # reintento

    assert len(avisos) == 1


def test_webhook_sin_firma_valida_es_rechazado(tienda_client, entorno_mp, monkeypatch):
    """Con MP_WEBHOOK_SECRET configurado, un webhook sin X-Signature debe dar 401."""
    monkeypatch.setenv('MP_WEBHOOK_SECRET', 'super-secreto')
    resp = _webhook(tienda_client)
    assert resp.status_code == 401


def test_fallo_consultando_mp_pide_reintento(tienda_client, entorno_mp, monkeypatch):
    """Si MP no responde, el webhook devuelve 500 para que MP reintente (no perder el pago)."""
    _crear_escenario()

    def fake_get(url, **kwargs):
        raise ConnectionError('MP caído')
    monkeypatch.setattr(tienda.requests, 'get', fake_get)
    monkeypatch.setattr(tienda.time, 'sleep', lambda s: None)  # no esperar el reintento

    resp = _webhook(tienda_client)
    assert resp.status_code == 500


# ─── Tests del flujo SALDO (pago de cuota restante) ────────────────

def _crear_pedido_con_saldo():
    """Crea un pedido ya facturado con saldo pendiente (para probar pago de SALDO)."""
    colegio = Colegio(nombre='COLEGIO SALDO', ciudad='Bogotá')
    producto = Producto(nombre='Pantalon Saldo', tipo='pantalon')
    db.session.add_all([colegio, producto])
    db.session.flush()

    precio = 80000
    item = {
        'id_producto': producto.id_producto, 'nombre': 'Pantalon Saldo',
        'talla': '10', 'cantidad': 1, 'precio_unitario': precio,
        'subtotal': precio, 'id_reserva': None, 'tipo_pedido': 'normal',
        'stock_disponible': 1,
    }
    pedido = PedidoWeb(
        referencia='RALOZ-SALDO001',
        nombre_cliente='Cliente Saldo', email_cliente='saldo@test.com',
        telefono_cliente='3109999999',
        id_colegio=colegio.id_colegio, nombre_colegio=colegio.nombre,
        items_json=json.dumps([item]),
        total=precio, total_orden=precio, abono_porcentaje=50,
        tiene_fabricacion=False, estado='pagado',
    )
    db.session.add(pedido)
    db.session.flush()

    # Factura con 50% abonado (saldo restante)
    factura = Factura(
        numero_factura='TEST-SALDO-001',
        id_colegio=colegio.id_colegio,
        usuario_creacion='TEST',
        cliente_nombre='Cliente Saldo',
        fecha_factura=date.today(),
        total=precio, subtotal=precio,
        total_abonado=precio * 0.5,
        saldo_pendiente=precio * 0.5,
        metodo_pago='MP', estado='PAGADA',
    )
    db.session.add(factura)
    db.session.flush()
    pedido.id_factura = factura.id_factura
    db.session.add(Pago(
        id_factura=factura.id_factura, valor=precio * 0.5,
        metodo_pago='MP', usuario_registro='TIENDA_WEB',
        fecha_pago=date.today(),
    ))
    db.session.commit()
    return pedido, factura, producto


def _mock_saldo_mp(monkeypatch, referencia, estado='approved', monto=40000):
    def fake_get(url, **kwargs):
        return _FakeResponse({
            'id': 888, 'status': estado,
            'external_reference': referencia,
            'payment_type_id': 'credit_card',
            'transaction_amount': monto,
        })
    monkeypatch.setattr(tienda.requests, 'get', fake_get)


def _saldo_webhook(client):
    return client.post('/api/tienda/mp/webhook', json={
        'type': 'payment', 'data': {'id': '888'},
    })


def test_pago_saldo_aprobado_cancela_saldo(tienda_client, entorno_mp, monkeypatch):
    """El pago del SALDO (-SALDO) descuenta el saldo pendiente y marca PAGADA."""
    pedido, factura, _ = _crear_pedido_con_saldo()
    _mock_saldo_mp(monkeypatch, 'RALOZ-SALDO001-SALDO')

    resp = _saldo_webhook(tienda_client)
    assert resp.status_code == 200

    db.session.refresh(factura)
    assert factura.saldo_pendiente == 0
    assert factura.estado == 'PAGADA'
    assert factura.mp_saldo_payment_id == '888'

    db.session.refresh(pedido)
    assert pedido.estado == 'pagado'

    # Se registró el Pago del saldo
    pagos_saldo = Pago.query.filter_by(id_factura=factura.id_factura).all()
    assert len(pagos_saldo) == 2  # 1 abono + 1 saldo


def test_pago_saldo_idempotente_no_descuenta_dos_veces(tienda_client, entorno_mp, monkeypatch):
    """MP reintenta el webhook del SALDO: no descuenta dos veces."""
    pedido, factura, _ = _crear_pedido_con_saldo()
    _mock_saldo_mp(monkeypatch, 'RALOZ-SALDO001-SALDO')

    assert _saldo_webhook(tienda_client).status_code == 200
    assert _saldo_webhook(tienda_client).status_code == 200  # reintento

    db.session.refresh(factura)
    assert factura.saldo_pendiente == 0
    assert factura.mp_saldo_payment_id == '888'
    # Solo 2 pagos: abono + un solo pago de saldo
    assert Pago.query.filter_by(id_factura=factura.id_factura).count() == 2


def test_pago_saldo_sin_referencia_existente(tienda_client, entorno_mp, monkeypatch):
    """Si el pedido base no existe, el webhook de SALDO retorna 200 (no rompe)."""
    _mock_saldo_mp(monkeypatch, 'RALOZ-NOEXISTE-SALDO')
    resp = _saldo_webhook(tienda_client)
    assert resp.status_code == 200


def test_contracargo_avisa_admin_y_no_toca_stock(tienda_client, entorno_mp, monkeypatch):
    """charged_back (contracargo real): avisa admin, no anula factura, no toca stock."""
    from app.api.tienda import publico as tienda
    avisos = []
    monkeypatch.setattr(tienda, '_avisar_admin', lambda texto: avisos.append(texto))

    # Crear pedido ya facturado y pagado
    _, producto, pedido, _ = _facturar(
        tienda_client, entorno_mp, monkeypatch,
        _crear_escenario(stock_inicial=5, cantidad=2))
    stock_tras_pago = Stock.query.filter_by(
        id_producto=producto.id_producto, talla_individual='8').first().cantidad

    _mock_pago_mp(monkeypatch, pedido.referencia, estado='charged_back')
    assert _webhook(tienda_client).status_code == 200

    db.session.refresh(pedido)
    assert pedido.estado == 'reembolsado'

    db.session.refresh(producto)
    factura = db.session.get(Factura, pedido.id_factura)
    assert factura.estado == 'PAGADA'  # intacta

    stock = Stock.query.filter_by(
        id_producto=producto.id_producto, talla_individual='8').first()
    assert stock.cantidad == stock_tras_pago  # sin cambios

    assert len(avisos) == 1
    assert 'contracargo' in avisos[0]

