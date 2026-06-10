"""
Tests del runner de migraciones versionadas (app/db_migrations.py).

Se prueban las mecánicas del runner con migraciones de juguete compatibles
con SQLite. El SQL real de MIGRACIONES es de PostgreSQL y solo corre en prod.
"""
import pytest
from sqlalchemy import text
from app import db
from app.db_migrations import aplicar_migraciones, _ejecutar_pendientes


def _versiones():
    rows = db.session.execute(
        text("SELECT version FROM schema_migrations ORDER BY version")
    ).fetchall()
    return [r[0] for r in rows]


def test_aplica_pendientes_en_orden_y_las_registra(app):
    migraciones = [
        {'version': '0001', 'descripcion': 'tabla a', 'sql': ['CREATE TABLE mig_a (id INTEGER)']},
        {'version': '0002', 'descripcion': 'tabla b', 'sql': ['CREATE TABLE mig_b (id INTEGER)']},
    ]
    _ejecutar_pendientes(migraciones)

    assert _versiones() == ['0001', '0002']
    # Las tablas existen
    db.session.execute(text('SELECT * FROM mig_a'))
    db.session.execute(text('SELECT * FROM mig_b'))


def test_no_reejecuta_migraciones_aplicadas(app):
    migraciones = [
        {'version': '0001', 'descripcion': 'inserta fila',
         'sql': ['CREATE TABLE mig_c (id INTEGER)', 'INSERT INTO mig_c VALUES (1)']},
    ]
    _ejecutar_pendientes(migraciones)
    _ejecutar_pendientes(migraciones)  # segunda corrida: no debe insertar otra fila

    filas = db.session.execute(text('SELECT COUNT(*) FROM mig_c')).scalar()
    assert filas == 1
    assert _versiones() == ['0001']


def test_fallo_detiene_la_cadena_y_no_registra(app):
    migraciones = [
        {'version': '0001', 'descripcion': 'ok', 'sql': ['CREATE TABLE mig_d (id INTEGER)']},
        {'version': '0002', 'descripcion': 'rota', 'sql': ['ESTO NO ES SQL VALIDO']},
        {'version': '0003', 'descripcion': 'nunca llega', 'sql': ['CREATE TABLE mig_e (id INTEGER)']},
    ]
    with pytest.raises(Exception):
        _ejecutar_pendientes(migraciones)

    # 0001 quedó aplicada; 0002 falló (no registrada); 0003 no se ejecutó
    assert _versiones() == ['0001']
    with pytest.raises(Exception):
        db.session.execute(text('SELECT * FROM mig_e'))
    db.session.rollback()


def test_migracion_fallida_se_reintenta_en_el_proximo_arranque(app):
    rota = [{'version': '0001', 'descripcion': 'rota', 'sql': ['ESTO NO ES SQL VALIDO']}]
    with pytest.raises(Exception):
        _ejecutar_pendientes(rota)

    # "Corregida" (mismo número de versión): el próximo arranque la aplica
    corregida = [{'version': '0001', 'descripcion': 'corregida', 'sql': ['CREATE TABLE mig_f (id INTEGER)']}]
    _ejecutar_pendientes(corregida)
    assert _versiones() == ['0001']
    db.session.execute(text('SELECT * FROM mig_f'))


def test_tolerante_falla_pero_se_marca_y_continua(app):
    migraciones = [
        {'version': '0001', 'descripcion': 'rename ya hecho', 'tolerante': True,
         'sql': ['ALTER TABLE tabla_inexistente RENAME COLUMN x TO y']},
        {'version': '0002', 'descripcion': 'sigue normal', 'sql': ['CREATE TABLE mig_g (id INTEGER)']},
    ]
    _ejecutar_pendientes(migraciones)  # no lanza

    assert _versiones() == ['0001', '0002']
    db.session.execute(text('SELECT * FROM mig_g'))


def test_en_sqlite_solo_create_all_sin_sql_postgres(app):
    """aplicar_migraciones() en SQLite no debe intentar el SQL de PostgreSQL."""
    aplicar_migraciones()  # no debe lanzar
    # No creó schema_migrations porque el SQL versionado es solo de PostgreSQL
    existe = db.session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )).fetchone()
    assert existe is None
