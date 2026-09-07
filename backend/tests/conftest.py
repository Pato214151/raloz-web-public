"""
Fixtures de prueba.

Monta una app Flask mínima con SQLite en memoria (sin los connect_args de
Postgres) para poder probar la lógica que toca la base de datos.
"""
import pytest
from flask import Flask
from app import db
import app.models  # noqa: F401  — registra todos los modelos en el metadata


@pytest.fixture
def app():
    application = Flask('test')
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(application)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def tienda_app():
    """App mínima con el blueprint de tienda registrado (endpoints públicos + admin)."""
    from app import jwt
    application = Flask('test')
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['JWT_SECRET_KEY'] = 'test-secret'
    application.config['RATELIMIT_ENABLED'] = False
    db.init_app(application)
    jwt.init_app(application)

    from app.api.tienda import tienda_bp
    application.register_blueprint(tienda_bp, url_prefix='/api/tienda')

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def tienda_client(tienda_app):
    return tienda_app.test_client()


@pytest.fixture(autouse=True)
def _sin_cierres_excepcionales():
    """Los tests no dependen del calendario real.

    CIERRES lleva fechas de días en que el local no atiende; el día que una de
    esas fechas llega, el bot antepone el aviso a toda respuesta y cualquier
    test que compare textos falla sin que nada esté roto. Se limpia por defecto;
    los tests del aviso lo reponen ellos mismos.
    """
    try:
        from app.bot import responses
    except Exception:
        yield
        return
    original = responses.CIERRES
    responses.CIERRES = {}
    try:
        yield
    finally:
        responses.CIERRES = original
