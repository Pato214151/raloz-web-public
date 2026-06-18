"""
Tests del módulo Órdenes de Producción (confección al taller).
App mínima con SQLite, igual que conftest.tienda_app.
"""
import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import db, jwt
import app.models  # noqa: F401  — registra modelos
from app.models import Colegio


@pytest.fixture
def op_app():
    application = Flask('test-op')
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['JWT_SECRET_KEY'] = 'test-secret'
    application.config['RATELIMIT_ENABLED'] = False
    db.init_app(application)
    jwt.init_app(application)

    from app.api.ordenes_produccion import ordenes_produccion_bp
    application.register_blueprint(ordenes_produccion_bp, url_prefix='/api/ordenes-produccion')

    with application.app_context():
        db.create_all()
        db.session.add(Colegio(nombre='MANYANET'))
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(op_app):
    return op_app.test_client()


def _token(app, rol='administrador'):
    with app.app_context():
        return create_access_token(identity='1', additional_claims={'usuario': 'tester', 'rol': rol})


def _auth(app, rol='administrador'):
    return {'Authorization': f'Bearer {_token(app, rol)}'}


def _payload():
    return {
        'prenda': 'Chaqueta Diario',
        'id_colegio': 1,
        'taller': 'Confecciones XYZ',
        'fecha_entrega': '2026-06-30',
        'insumos': [{'insumo': 'Tela principal', 'especificacion': 'Antifluido', 'cantidad': '105', 'unidad': 'mts'}],
        'tallas': [{'talla': '6-8', 'cantidad': 40}, {'talla': 'XL', 'cantidad': 20}],
        'logo_descripcion': 'Escudo', 'logo_tecnica': 'Bordado',
        'costo_tela': 630000, 'costo_mano_obra': 450000,
    }


def test_crear_orden_admin(op_app, client):
    r = client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app))
    assert r.status_code == 201, r.get_data(as_text=True)
    d = r.get_json()
    assert d['numero'] == 1 and d['numero_fmt'] == 'ORD-0001'
    assert d['nombre_colegio'] == 'MANYANET'   # tomado de la BD por id_colegio
    assert d['total_prendas'] == 60            # 40 + 20
    assert d['costo_total'] == 1080000


def test_numero_consecutivo(op_app, client):
    client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app))
    r2 = client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app))
    assert r2.get_json()['numero'] == 2


def test_listar_y_pdf(op_app, client):
    cr = client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app))
    oid = cr.get_json()['id_orden']

    lst = client.get('/api/ordenes-produccion', headers=_auth(op_app))
    assert lst.status_code == 200
    assert lst.get_json()['total'] == 1

    pdf = client.get(f'/api/ordenes-produccion/{oid}/pdf', headers=_auth(op_app))
    assert pdf.status_code == 200
    assert pdf.mimetype == 'application/pdf'
    assert pdf.get_data()[:5] == b'%PDF-'


def test_prenda_obligatoria(op_app, client):
    p = _payload(); p['prenda'] = ''
    r = client.post('/api/ordenes-produccion', json=p, headers=_auth(op_app))
    assert r.status_code == 400


def test_solo_admin(op_app, client):
    # vendedor NO puede crear ni listar
    assert client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app, 'vendedor')).status_code == 403
    assert client.get('/api/ordenes-produccion', headers=_auth(op_app, 'vendedor')).status_code == 403
    # sin token tampoco
    assert client.get('/api/ordenes-produccion').status_code == 401


def test_eliminar(op_app, client):
    oid = client.post('/api/ordenes-produccion', json=_payload(), headers=_auth(op_app)).get_json()['id_orden']
    assert client.delete(f'/api/ordenes-produccion/{oid}', headers=_auth(op_app)).status_code == 200
    assert client.get('/api/ordenes-produccion', headers=_auth(op_app)).get_json()['total'] == 0
