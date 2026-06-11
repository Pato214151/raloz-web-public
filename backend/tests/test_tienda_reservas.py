"""
Tests del flujo de reservas de la tienda pública:
  - POST /api/tienda/reservar/liberar (libera stock al quitar items del carrito)
  - Protección JWT de los endpoints /admin/* de tienda.py
"""
import pytest
from app import db
from app.models import Colegio, Producto, Stock, Reserva


@pytest.fixture
def client(tienda_client):
    return tienda_client


def _crear_datos_base():
    colegio = Colegio(nombre='COLEGIO TEST', ciudad='Bogotá')
    producto = Producto(nombre='Camisa Test', tipo='camisa')
    db.session.add_all([colegio, producto])
    db.session.flush()
    db.session.add(Stock(
        id_colegio=colegio.id_colegio,
        id_producto=producto.id_producto,
        talla_individual='8',
        cantidad=5,
    ))
    db.session.commit()
    return colegio, producto


def _reservar(client, session_id, colegio, producto, cantidad=2):
    resp = client.post('/api/tienda/reservar', json={
        'session_id': session_id,
        'id_colegio': colegio.id_colegio,
        'id_producto': producto.id_producto,
        'talla': '8',
        'cantidad': cantidad,
    })
    assert resp.status_code in (200, 201), resp.get_json()
    return resp.get_json()['id_reserva']


# ── POST /reservar/liberar ──────────────────────────────────────────

def test_liberar_reserva_por_id(client):
    colegio, producto = _crear_datos_base()
    id_reserva = _reservar(client, 'sesion-A', colegio, producto)

    resp = client.post('/api/tienda/reservar/liberar', json={
        'session_id': 'sesion-A',
        'ids_reserva': [id_reserva],
    })
    assert resp.status_code == 200
    assert resp.get_json()['liberadas'] == 1
    assert db.session.get(Reserva, id_reserva).estado == 'cancelada'


def test_liberar_todas_las_reservas_de_la_sesion(client):
    colegio, producto = _crear_datos_base()
    _reservar(client, 'sesion-A', colegio, producto, cantidad=1)

    resp = client.post('/api/tienda/reservar/liberar', json={'session_id': 'sesion-A'})
    assert resp.status_code == 200
    assert resp.get_json()['liberadas'] == 1
    activas = Reserva.query.filter_by(session_id='sesion-A', estado='activa').count()
    assert activas == 0


def test_no_libera_reservas_de_otra_sesion(client):
    colegio, producto = _crear_datos_base()
    id_reserva = _reservar(client, 'sesion-A', colegio, producto)

    # sesion-B intenta liberar la reserva de sesion-A (incluso conociendo el id)
    resp = client.post('/api/tienda/reservar/liberar', json={
        'session_id': 'sesion-B',
        'ids_reserva': [id_reserva],
    })
    assert resp.status_code == 200
    assert resp.get_json()['liberadas'] == 0
    assert db.session.get(Reserva, id_reserva).estado == 'activa'


def test_liberar_sin_session_id_da_400(client):
    resp = client.post('/api/tienda/reservar/liberar', json={})
    assert resp.status_code == 400


def test_liberar_ids_invalidos_da_400(client):
    resp = client.post('/api/tienda/reservar/liberar', json={
        'session_id': 'sesion-A',
        'ids_reserva': ['no-es-numero'],
    })
    assert resp.status_code == 400


def test_stock_liberado_vuelve_a_estar_disponible(client):
    """Tras liberar, otra sesión puede reservar el stock que estaba bloqueado."""
    colegio, producto = _crear_datos_base()
    _reservar(client, 'sesion-A', colegio, producto, cantidad=5)  # agota el stock

    # sesion-B no puede reservar (todo bloqueado por sesion-A)
    resp = client.post('/api/tienda/reservar', json={
        'session_id': 'sesion-B',
        'id_colegio': colegio.id_colegio,
        'id_producto': producto.id_producto,
        'talla': '8',
        'cantidad': 1,
    })
    assert resp.status_code == 409

    # sesion-A libera su carrito → sesion-B ya puede reservar
    client.post('/api/tienda/reservar/liberar', json={'session_id': 'sesion-A'})
    resp = client.post('/api/tienda/reservar', json={
        'session_id': 'sesion-B',
        'id_colegio': colegio.id_colegio,
        'id_producto': producto.id_producto,
        'talla': '8',
        'cantidad': 1,
    })
    assert resp.status_code in (200, 201)


# ── Protección JWT de los endpoints admin ──────────────────────────

ENDPOINTS_ADMIN = [
    ('GET',  '/api/tienda/admin/pedidos/conteo-nuevos'),
    ('GET',  '/api/tienda/admin/pedidos'),
    ('GET',  '/api/tienda/admin/pedidos/1'),
    ('POST', '/api/tienda/admin/pedidos/1/marcar-pagado'),
    ('POST', '/api/tienda/admin/pedidos/1/generar-factura'),
    ('POST', '/api/tienda/admin/pedidos/1/reenviar-email'),
    ('POST', '/api/tienda/admin/pedidos/1/actualizar-entrega'),
    ('GET',  '/api/tienda/admin/pedidos/1/factura.pdf'),
    ('GET',  '/api/tienda/admin/fabricacion/pedidos'),
    ('GET',  '/api/tienda/admin/fabricacion/pedidos/1'),
    ('POST', '/api/tienda/admin/fabricacion/pedidos/1/marcar-listo'),
    ('POST', '/api/tienda/admin/fabricacion/pedidos/1/marcar-entregado'),
    ('POST', '/api/tienda/admin/fabricacion/pedidos/1/marcar-notificado'),
    ('POST', '/api/tienda/admin/fabricacion/pedidos/1/registrar-saldo'),
    ('POST', '/api/tienda/admin/fabricacion/pedidos/1/actualizar-fecha'),
    ('GET',  '/api/tienda/admin/fabricacion/stock-pendiente'),
    ('POST', '/api/tienda/admin/fabricacion/stock-pendiente/registrar'),
]


@pytest.mark.parametrize('metodo,url', ENDPOINTS_ADMIN)
def test_endpoints_admin_sin_token_dan_401(client, metodo, url):
    resp = client.open(url, method=metodo)
    assert resp.status_code == 401, f'{metodo} {url} no exige JWT (status {resp.status_code})'


# ── Control de rol: pedidos online → administrador + vendedor ──────

def _token(tienda_app, rol):
    from flask_jwt_extended import create_access_token
    with tienda_app.app_context():
        return create_access_token(identity='1', additional_claims={'usuario': 'tester', 'rol': rol})


@pytest.mark.parametrize('metodo,url', ENDPOINTS_ADMIN)
def test_cajero_no_puede_gestionar_pedidos(tienda_app, client, metodo, url):
    """El cajero queda fuera: debe recibir 403 en los endpoints admin de tienda."""
    headers = {'Authorization': f'Bearer {_token(tienda_app, "cajero")}'}
    resp = client.open(url, method=metodo, headers=headers)
    assert resp.status_code == 403, f'{metodo} {url} dejó pasar a cajero (status {resp.status_code})'


@pytest.mark.parametrize('rol', ['administrador', 'vendedor'])
def test_admin_y_vendedor_pasan_la_autorizacion(tienda_app, client, rol):
    """admin y vendedor superan la capa de auth (no 401/403); el 404 por falta de
    datos confirma que llegaron al handler."""
    headers = {'Authorization': f'Bearer {_token(tienda_app, rol)}'}
    resp = client.open('/api/tienda/admin/pedidos/999', method='GET', headers=headers)
    assert resp.status_code not in (401, 403), f'{rol} fue bloqueado (status {resp.status_code})'


# ── Conteo de pedidos nuevos (badge del panel) ─────────────────────

def test_conteo_pedidos_nuevos(tienda_app, client):
    """Cuenta pedidos pagados con factura en POR_ENTREGAR; ignora los empacados."""
    from datetime import date
    from app.models import PedidoWeb, Factura, Colegio
    headers = {'Authorization': f'Bearer {_token(tienda_app, "administrador")}'}

    col = Colegio(nombre='COL CONTEO', ciudad='Bogotá')
    db.session.add(col)
    db.session.flush()
    cid = col.id_colegio

    def conteo():
        r = client.get('/api/tienda/admin/pedidos/conteo-nuevos', headers=headers)
        assert r.status_code == 200
        return r.get_json()['nuevos']

    assert conteo() == 0  # sin pedidos

    # Factura POR_ENTREGAR + pedido pagado → cuenta como nuevo
    f1 = Factura(numero_factura='FAC-T-1', id_colegio=cid, total=1000, estado='PAGADA', estado_entrega='POR_ENTREGAR', fecha_factura=date.today(), usuario_creacion='TEST')
    db.session.add(f1)
    db.session.flush()
    db.session.add(PedidoWeb(
        referencia='R-NUEVO-1', nombre_cliente='X', email_cliente='x@x.com',
        items_json='[]', total=1000, estado='pagado', id_factura=f1.id_factura,
    ))
    # Otro ya empacado → NO debe contar
    f2 = Factura(numero_factura='FAC-T-2', id_colegio=cid, total=1000, estado='PAGADA', estado_entrega='EMPACADO', fecha_factura=date.today(), usuario_creacion='TEST')
    db.session.add(f2)
    db.session.flush()
    db.session.add(PedidoWeb(
        referencia='R-EMP-1', nombre_cliente='Y', email_cliente='y@y.com',
        items_json='[]', total=1000, estado='pagado', id_factura=f2.id_factura,
    ))
    db.session.commit()

    assert conteo() == 1  # solo el POR_ENTREGAR


def test_vista_activos_solo_pagados_sin_entregar(tienda_app, client):
    """vista=activos muestra solo pagados sin entregar (POR_ENTREGAR/EMPACADO),
    ocultando entregados y cancelados."""
    from datetime import date
    from app.models import PedidoWeb, Factura, Colegio
    headers = {'Authorization': f'Bearer {_token(tienda_app, "administrador")}'}

    col = Colegio(nombre='COL ACTIVOS', ciudad='Bogotá')
    db.session.add(col)
    db.session.flush()
    cid = col.id_colegio

    def mk(ref, estado_entrega):
        f = Factura(numero_factura=f'FAC-{ref}', id_colegio=cid, total=1000, estado='PAGADA',
                    estado_entrega=estado_entrega, fecha_factura=date.today(), usuario_creacion='T')
        db.session.add(f)
        db.session.flush()
        db.session.add(PedidoWeb(referencia=ref, nombre_cliente='X', email_cliente='x@x.com',
                                 items_json='[]', total=1000, estado='pagado', id_factura=f.id_factura))

    mk('A-POR', 'POR_ENTREGAR')   # aparece
    mk('A-EMP', 'EMPACADO')       # aparece
    mk('A-ENT', 'ENTREGADO')      # NO aparece (ya entregado)
    db.session.add(PedidoWeb(referencia='A-CANC', nombre_cliente='Y', email_cliente='y@y.com',
                             items_json='[]', total=1000, estado='cancelado'))  # NO aparece
    db.session.commit()

    r = client.get('/api/tienda/admin/pedidos?vista=activos', headers=headers)
    assert r.status_code == 200
    refs = {p['referencia'] for p in r.get_json()['pedidos']}
    assert refs == {'A-POR', 'A-EMP'}
