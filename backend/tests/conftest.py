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
