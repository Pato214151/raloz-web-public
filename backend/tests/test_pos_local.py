"""
Tests del flujo POS local: crear/editar/anular factura, pagos y caja.

Red de seguridad para la Fase 2 (ver docs/ARQUITECTURA.md §5): documentan el
comportamiento vigente del punto de venta antes de tocar duplicaciones y bugs.
"""
import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import db
import app.models  # noqa: F401
from app.models import (
    Colegio, Producto, PrecioColegio, Stock, Factura, Pago,
    PrendaPendiente, MovimientoInventario, CajaDiaria, MovimientoCaja,
)


@pytest.fixture
def pos_app():
    """App mínima con los blueprints del POS local registrados."""
    from app import jwt
    application = Flask('test-pos')
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['JWT_SECRET_KEY'] = 'test-secret'
    db.init_app(application)
    jwt.init_app(application)

    from app.api.facturas import facturas_bp
    from app.api.pagos import pagos_bp
    from app.api.caja import caja_bp
    from app.api.prendas_pendientes import prendas_bp
    application.register_blueprint(facturas_bp, url_prefix='/api/facturas')
    application.register_blueprint(pagos_bp, url_prefix='/api/pagos')
    application.register_blueprint(caja_bp, url_prefix='/api/caja')
    application.register_blueprint(prendas_bp, url_prefix='/api/prendas')

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(pos_app):
    return pos_app.test_client()


@pytest.fixture
def auth(pos_app):
    token = create_access_token(identity='1', additional_claims={'usuario': 'test', 'rol': 'administrador'})
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def datos_base(pos_app):
    """Colegio + producto con precio ($50.000 grupo 6-8) y stock (5 und talla 6)."""
    colegio = Colegio(nombre='Colegio Test', activo=True)
    producto = Producto(nombre='Camisa Test', tipo='Diario', codigo='CAM-T', activo=True)
    db.session.add_all([colegio, producto])
    db.session.flush()
    db.session.add(PrecioColegio(id_colegio=colegio.id_colegio, id_producto=producto.id_producto,
                                 talla_grupo='6-8', precio_unitario=50000))
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=producto.id_producto,
                         talla_individual='6', cantidad=5))
    db.session.commit()
    return {'colegio': colegio, 'producto': producto}


def _payload_factura(datos, **extra):
    base = {
        'id_colegio': datos['colegio'].id_colegio,
        'cliente_nombre': 'Cliente Prueba',
        'cliente_telefono': '3001234567',
        'detalles': [{
            'id_producto': datos['producto'].id_producto,
            'talla_individual': '6',
            'cantidad': 2,
            'precio_unitario': 50000,
        }],
    }
    base.update(extra)
    return base


# ══════════════════════════════════════════════════════════════
# Crear factura
# ══════════════════════════════════════════════════════════════

def test_crear_factura_inmediata_descuenta_stock_y_kardex(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, entrega_inmediata=True, abono=100000, metodo_pago='EFECTIVO'), headers=auth)
    assert r.status_code == 201, r.get_json()
    f = r.get_json()['factura']
    assert f['total'] == 100000
    assert f['estado'] == 'PAGADA'

    stock = Stock.query.filter_by(talla_individual='6').first()
    assert stock.cantidad == 3  # 5 - 2

    mov = MovimientoInventario.query.filter_by(tipo='SALIDA').first()
    assert mov is not None and mov.cantidad == 2 and mov.stock_resultante == 3
    assert mov.referencia == f['numero_factura']


def test_crear_factura_por_entregar_no_toca_stock_y_crea_prenda(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    assert r.status_code == 201
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5  # intacto
    prenda = PrendaPendiente.query.first()
    assert prenda is not None and prenda.estado == 'PENDIENTE' and prenda.cantidad == 2
    assert MovimientoInventario.query.count() == 0


def test_crear_factura_inmediata_sin_stock_da_409_con_faltantes(client, auth, datos_base):
    payload = _payload_factura(datos_base, entrega_inmediata=True)
    payload['detalles'][0]['cantidad'] = 99
    r = client.post('/api/facturas', json=payload, headers=auth)
    assert r.status_code == 409
    body = r.get_json()
    assert body['code'] == 'sin_stock_suficiente'
    assert body['faltantes'][0]['disponible'] == 5


def test_crear_factura_usa_precio_autoritativo_de_bd(client, auth, datos_base):
    payload = _payload_factura(datos_base)
    payload['detalles'][0]['precio_unitario'] = 1000  # cliente intenta pagar menos
    r = client.post('/api/facturas', json=payload, headers=auth)
    assert r.status_code == 201
    assert r.get_json()['factura']['total'] == 100000  # 2 × 50.000 de la BD


def test_crear_factura_abono_parcial_queda_pendiente(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(datos_base, abono=30000), headers=auth)
    f = r.get_json()['factura']
    assert f['estado'] == 'PENDIENTE'
    assert f['total_abonado'] == 30000
    assert f['saldo_pendiente'] == 70000


def test_crear_factura_efectivo_con_caja_abierta_registra_ingreso(client, auth, datos_base):
    client.post('/api/caja/abrir', json={'monto_inicial': 20000}, headers=auth)
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, abono=100000, metodo_pago='EFECTIVO'), headers=auth)
    assert r.status_code == 201
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    assert caja.total_ventas == 100000
    assert caja.monto_esperado == 120000
    mov = MovimientoCaja.query.filter_by(tipo='INGRESO').first()
    assert mov is not None and mov.valor == 100000


def test_crear_factura_upsert_cliente_por_telefono(client, auth, datos_base):
    from app.models import Cliente
    client.post('/api/facturas', json=_payload_factura(datos_base, abono=100000), headers=auth)
    client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    clientes = Cliente.query.filter_by(telefono='3001234567').all()
    assert len(clientes) == 1
    assert clientes[0].cantidad_facturas == 2


# ══════════════════════════════════════════════════════════════
# Pagos
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def factura_pendiente(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(datos_base, abono=30000), headers=auth)
    return r.get_json()['factura']


def test_pago_completa_factura(client, auth, factura_pendiente):
    r = client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 70000, 'metodo_pago': 'NEQUI',
    }, headers=auth)
    assert r.status_code == 201
    body = r.get_json()
    assert body['saldo_restante'] == 0
    assert body['factura']['estado'] == 'PAGADA'


def test_pago_no_puede_exceder_saldo(client, auth, factura_pendiente):
    r = client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 999999,
    }, headers=auth)
    assert r.status_code == 400
    assert r.get_json()['saldo'] == 70000


def test_pago_rechazado_en_factura_anulada(client, auth, factura_pendiente):
    client.post(f"/api/facturas/{factura_pendiente['id_factura']}/anular", headers=auth)
    r = client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 1000,
    }, headers=auth)
    assert r.status_code == 400


def test_eliminar_pago_recalcula_factura(client, auth, factura_pendiente):
    pago = Pago.query.filter_by(id_factura=factura_pendiente['id_factura']).first()
    r = client.delete(f'/api/pagos/{pago.id_pago}', headers=auth)
    assert r.status_code == 200
    f = Factura.query.get(factura_pendiente['id_factura'])
    assert f.total_abonado == 0
    assert f.saldo_pendiente == 100000
    assert f.estado == 'PENDIENTE'


def test_pago_saldo_efectivo_entra_a_caja(client, auth, factura_pendiente):
    """Antes solo el abono inicial entraba a la caja; el saldo en efectivo no."""
    client.post('/api/caja/abrir', json={'monto_inicial': 10000}, headers=auth)
    r = client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 70000, 'metodo_pago': 'EFECTIVO',
    }, headers=auth)
    assert r.status_code == 201
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    assert caja.total_ventas == 70000
    assert caja.monto_esperado == 80000
    mov = MovimientoCaja.query.filter_by(tipo='INGRESO').first()
    assert mov is not None and 'Abono factura' in mov.concepto


def test_pago_saldo_no_efectivo_no_toca_caja(client, auth, factura_pendiente):
    client.post('/api/caja/abrir', json={'monto_inicial': 10000}, headers=auth)
    client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 70000, 'metodo_pago': 'NEQUI',
    }, headers=auth)
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    assert (caja.total_ventas or 0) == 0
    assert MovimientoCaja.query.count() == 0


def test_pago_saldo_efectivo_sin_caja_abierta_no_falla(client, auth, factura_pendiente):
    r = client.post('/api/pagos', json={
        'id_factura': factura_pendiente['id_factura'], 'valor': 70000, 'metodo_pago': 'EFECTIVO',
    }, headers=auth)
    assert r.status_code == 201
    assert MovimientoCaja.query.count() == 0


# ══════════════════════════════════════════════════════════════
# Anular / reactivar
# ══════════════════════════════════════════════════════════════

def test_anular_factura_inmediata_devuelve_stock(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, entrega_inmediata=True), headers=auth)
    fid = r.get_json()['factura']['id_factura']
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 3

    r = client.post(f'/api/facturas/{fid}/anular', headers=auth)
    assert r.status_code == 200
    assert r.get_json()['factura']['estado'] == 'ANULADA'
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5


def test_anular_por_entregar_no_devuelve_stock(client, auth, datos_base):
    """Una venta 'por entregar' nunca descontó stock: anularla no debe inflarlo."""
    r = client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    fid = r.get_json()['factura']['id_factura']
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5

    r = client.post(f'/api/facturas/{fid}/anular', headers=auth)
    assert r.status_code == 200
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5  # sigue igual


def test_anular_registra_entrada_en_kardex(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, entrega_inmediata=True), headers=auth)
    f = r.get_json()['factura']
    client.post(f"/api/facturas/{f['id_factura']}/anular", headers=auth)
    entrada = MovimientoInventario.query.filter_by(
        tipo='ENTRADA', referencia=f['numero_factura']).first()
    assert entrada is not None and entrada.cantidad == 2
    assert entrada.motivo == 'Anulación factura'


def test_anular_tras_reactivar_no_devuelve_doble(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, entrega_inmediata=True), headers=auth)
    fid = r.get_json()['factura']['id_factura']
    client.post(f'/api/facturas/{fid}/anular', headers=auth)      # 3 → 5
    client.post(f'/api/facturas/{fid}/reactivar', headers=auth)   # no toca stock
    client.post(f'/api/facturas/{fid}/anular', headers=auth)      # neto ya es 0
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5


def test_editar_factura_inmediata_mantiene_kardex_consistente(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(
        datos_base, entrega_inmediata=True), headers=auth)
    f = r.get_json()['factura']
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 3

    # Cambiar la cantidad de 2 a 1: devuelve 2 y descuenta 1
    r = client.put(f"/api/facturas/{f['id_factura']}", json={
        'detalles': [{
            'id_producto': datos_base['producto'].id_producto,
            'talla_individual': '6', 'cantidad': 1, 'precio_unitario': 50000,
        }],
    }, headers=auth)
    assert r.status_code == 200
    stock = Stock.query.filter_by(talla_individual='6').first()
    assert stock.cantidad == 4  # 5 − 1

    # Kardex refleja todo: SALIDA 2 (venta), ENTRADA 2 (devolución), SALIDA 1 (edición)
    ultimo = (MovimientoInventario.query
              .order_by(MovimientoInventario.id.desc()).first())
    assert ultimo.stock_resultante == stock.cantidad


def test_editar_factura_por_entregar_no_toca_stock(client, auth, datos_base):
    r = client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    fid = r.get_json()['factura']['id_factura']
    r = client.put(f'/api/facturas/{fid}', json={
        'detalles': [{
            'id_producto': datos_base['producto'].id_producto,
            'talla_individual': '6', 'cantidad': 3, 'precio_unitario': 50000,
        }],
    }, headers=auth)
    assert r.status_code == 200
    assert Stock.query.filter_by(talla_individual='6').first().cantidad == 5
    assert MovimientoInventario.query.count() == 0


def test_reactivar_factura_recalcula_estado(client, auth, factura_pendiente):
    fid = factura_pendiente['id_factura']
    client.post(f'/api/facturas/{fid}/anular', headers=auth)
    r = client.post(f'/api/facturas/{fid}/reactivar', headers=auth)
    assert r.status_code == 200
    assert r.get_json()['factura']['estado'] == 'PENDIENTE'  # tiene abono parcial


# ══════════════════════════════════════════════════════════════
# Caja
# ══════════════════════════════════════════════════════════════

def test_caja_no_permite_doble_apertura(client, auth):
    assert client.post('/api/caja/abrir', json={'monto_inicial': 10000}, headers=auth).status_code == 201
    assert client.post('/api/caja/abrir', json={'monto_inicial': 5000}, headers=auth).status_code == 400


def test_caja_cierre_calcula_diferencia(client, auth):
    client.post('/api/caja/abrir', json={'monto_inicial': 10000}, headers=auth)
    client.post('/api/caja/movimiento', json={
        'tipo': 'INGRESO', 'monto': 50000, 'concepto': 'Venta manual'}, headers=auth)
    client.post('/api/caja/movimiento', json={
        'tipo': 'EGRESO', 'monto': 20000, 'concepto': 'Almuerzo'}, headers=auth)
    r = client.post('/api/caja/cerrar', json={'monto_real': 35000}, headers=auth)
    assert r.status_code == 200
    caja = r.get_json()['caja']
    assert caja['monto_esperado'] == 40000  # 10.000 + 50.000 − 20.000
    assert caja['diferencia'] == -5000


# ══════════════════════════════════════════════════════════════
# Prendas pendientes
# ══════════════════════════════════════════════════════════════

def test_entregar_batch_marca_solo_pendientes(client, auth, datos_base):
    # Dos facturas por entregar → dos prendas pendientes
    client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    prendas = PrendaPendiente.query.all()
    assert len(prendas) == 2
    ids = [p.id_pendiente for p in prendas]

    # Una ya está entregada → el batch debe omitirla
    client.post(f'/api/prendas/{ids[0]}/entregar', headers=auth)

    r = client.post('/api/prendas/entregar-batch', json={'ids': ids}, headers=auth)
    assert r.status_code == 200
    body = r.get_json()
    assert body['entregadas'] == 1 and body['omitidas'] == 1
    assert all(p.estado == 'ENTREGADO' for p in PrendaPendiente.query.all())

    # Validación de entrada
    assert client.post('/api/prendas/entregar-batch', json={}, headers=auth).status_code == 400
    assert client.post('/api/prendas/entregar-batch', json={'ids': ['x']}, headers=auth).status_code == 400


def test_entregar_prenda_individual(client, auth, datos_base):
    client.post('/api/facturas', json=_payload_factura(datos_base), headers=auth)
    prenda = PrendaPendiente.query.first()
    r = client.post(f'/api/prendas/{prenda.id_pendiente}/entregar', headers=auth)
    assert r.status_code == 200
    assert PrendaPendiente.query.get(prenda.id_pendiente).estado == 'ENTREGADO'
    # No se puede entregar dos veces
    assert client.post(f'/api/prendas/{prenda.id_pendiente}/entregar', headers=auth).status_code == 400
