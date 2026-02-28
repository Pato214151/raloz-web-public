"""
RALOZ COL SAS - Endpoint de Migración (TEMPORAL)
Recibe datos en JSON y los inserta en PostgreSQL.
ELIMINAR después de migrar.
"""

from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import text
import os

migracion_bp = Blueprint('migracion', __name__)

# Clave temporal para migración — ELIMINAR este archivo después de migrar
MIGRATION_KEY = os.getenv('MIGRATION_KEY', 'raloz-migracion-2026-temporal')


@migracion_bp.route('/ejecutar', methods=['POST'])
def ejecutar_migracion():
    """Recibe SQL statements y los ejecuta contra la DB"""
    # Verificar clave
    key = request.headers.get('X-Migration-Key', '')
    if key != MIGRATION_KEY:
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json()
    if not data or 'statements' not in data:
        return jsonify({'error': 'Se requiere "statements" (lista de SQL)'}), 400

    statements = data['statements']
    resultados = []
    errores = []

    try:
        for i, stmt in enumerate(statements):
            try:
                db.session.execute(text(stmt))
                resultados.append(f"OK [{i+1}]")
            except Exception as e:
                err_msg = f"Error [{i+1}]: {str(e)[:200]}"
                errores.append(err_msg)
                db.session.rollback()
                # Continuar con el siguiente
                continue

        db.session.commit()

        return jsonify({
            'ok': True,
            'ejecutados': len(resultados),
            'errores_count': len(errores),
            'errores': errores[:20],  # Max 20 errores en respuesta
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@migracion_bp.route('/limpiar', methods=['POST'])
def limpiar_tablas():
    """Limpia tablas antes de migrar (opcional)"""
    key = request.headers.get('X-Migration-Key', '')
    if key != MIGRATION_KEY:
        return jsonify({'error': 'No autorizado'}), 403

    tablas_orden = [
        'gastos', 'pagos', 'factura_detalle', 'facturas',
        'stock', 'precios_colegio', 'clientes',
        'metodos_pago', 'series_facturacion', 'productos', 'colegios'
    ]

    resultados = []
    for tabla in tablas_orden:
        try:
            result = db.session.execute(text(f"DELETE FROM {tabla}"))
            resultados.append(f"{tabla}: {result.rowcount} eliminados")
        except Exception as e:
            resultados.append(f"{tabla}: ERROR - {str(e)[:100]}")

    db.session.commit()
    return jsonify({'ok': True, 'resultados': resultados})


@migracion_bp.route('/verificar', methods=['GET'])
def verificar_migracion():
    """Verifica conteo de registros en cada tabla"""
    tablas = [
        'usuarios', 'colegios', 'productos', 'metodos_pago', 'series_facturacion',
        'series_remision', 'precios_colegio', 'stock', 'clientes',
        'facturas', 'factura_detalle', 'pagos', 'gastos',
        'stock_pendiente', 'prendas_pendientes', 'empaque_pendientes',
        'caja_diaria', 'movimientos_caja', 'auditoria'
    ]

    conteos = {}
    for tabla in tablas:
        try:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
            conteos[tabla] = result.scalar()
        except Exception as e:
            conteos[tabla] = f"ERROR: {str(e)[:100]}"

    return jsonify({'ok': True, 'tablas': conteos})
