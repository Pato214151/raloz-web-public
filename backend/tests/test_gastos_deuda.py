"""
Tests del flujo de DEUDA en gastos:
  - crear una deuda → estado_pago PENDIENTE (no cuenta como gasto)
  - listarla con estado_pago=PENDIENTE
  - marcarla pagada → PAGADO, fechada el día del pago
"""
import pytest
from datetime import date
from flask import Flask
from app import db, jwt
import app.models  # noqa: F401


@pytest.fixture
def gastos_app():
    application = Flask('test')
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['JWT_SECRET_KEY'] = 'test'
    application.config['RATELIMIT_ENABLED'] = False
    db.init_app(application)
    jwt.init_app(application)
    from app.api.gastos import gastos_bp
    application.register_blueprint(gastos_bp, url_prefix='/api/gastos')
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def _token(app, rol='administrador'):
    from flask_jwt_extended import create_access_token
    with app.app_context():
        return create_access_token(identity='1', additional_claims={'usuario': 't', 'rol': rol})


def test_deuda_no_cuenta_hasta_pagarse(gastos_app):
    client = gastos_app.test_client()
    h = {'Authorization': f'Bearer {_token(gastos_app)}'}

    # Crear una deuda
    r = client.post('/api/gastos', json={
        'descripcion': 'Tela proveedor', 'valor': 500000,
        'categoria': 'Costo Mercancía', 'es_deuda': True,
    }, headers=h)
    assert r.status_code == 201
    g = r.get_json()['gasto']
    assert g['estado_pago'] == 'PENDIENTE'
    gid = g['id_gasto']

    # Aparece al filtrar por deudas pendientes
    r = client.get('/api/gastos?estado_pago=PENDIENTE', headers=h)
    assert r.status_code == 200
    assert len(r.get_json()['gastos']) == 1

    # Marcarla pagada → se convierte en gasto del día de hoy
    r = client.post(f'/api/gastos/{gid}/pagar', json={'metodo_pago': 'EFECTIVO'}, headers=h)
    assert r.status_code == 200
    g2 = r.get_json()['gasto']
    assert g2['estado_pago'] == 'PAGADO'
    assert g2['fecha_pago'] == date.today().isoformat()
    assert g2['fecha'] == date.today().isoformat()

    # Pagarla otra vez → error (ya no es deuda)
    r = client.post(f'/api/gastos/{gid}/pagar', json={}, headers=h)
    assert r.status_code == 400


def test_gasto_normal_es_pagado(gastos_app):
    client = gastos_app.test_client()
    h = {'Authorization': f'Bearer {_token(gastos_app)}'}
    r = client.post('/api/gastos', json={
        'descripcion': 'Arriendo', 'valor': 1000000, 'categoria': 'Arriendo',
    }, headers=h)
    assert r.status_code == 201
    assert r.get_json()['gasto']['estado_pago'] == 'PAGADO'
