"""
API de Caja Diaria
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import CajaDiaria, MovimientoCaja
from app.utils.decorators import rol_requerido, get_current_identity
from datetime import datetime

caja_bp = Blueprint('caja', __name__)


@caja_bp.route('/actual', methods=['GET'])
@jwt_required()
def caja_actual():
    """Obtener caja abierta actual"""
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').order_by(CajaDiaria.fecha_apertura.desc()).first()
    if not caja:
        return jsonify({'caja': None, 'message': 'No hay caja abierta'}), 200
    return jsonify({'caja': caja.to_dict()}), 200


@caja_bp.route('/abrir', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def abrir_caja():
    """Abrir caja diaria"""
    identity = get_current_identity()
    data = request.get_json()

    # Verificar que no haya caja abierta
    caja_abierta = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    if caja_abierta:
        return jsonify({'error': 'Ya hay una caja abierta', 'caja': caja_abierta.to_dict()}), 400

    monto_inicial = float(data.get('monto_inicial', 0))

    caja = CajaDiaria(
        fecha_apertura=datetime.utcnow(),
        usuario_apertura=identity['usuario'],
        monto_inicial=monto_inicial,
        monto_esperado=monto_inicial,
    )
    db.session.add(caja)
    db.session.commit()

    return jsonify({'message': 'Caja abierta', 'caja': caja.to_dict()}), 201


@caja_bp.route('/cerrar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def cerrar_caja():
    """Cerrar caja diaria"""
    identity = get_current_identity()
    data = request.get_json()

    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    if not caja:
        return jsonify({'error': 'No hay caja abierta'}), 400

    monto_real = float(data.get('monto_real', 0))

    caja.fecha_cierre = datetime.utcnow()
    caja.usuario_cierre = identity['usuario']
    caja.monto_real = monto_real
    caja.diferencia = monto_real - caja.monto_esperado
    caja.estado = 'CERRADA'
    caja.observaciones = data.get('observaciones', '')

    db.session.commit()

    return jsonify({'message': 'Caja cerrada', 'caja': caja.to_dict()}), 200


@caja_bp.route('/movimientos', methods=['GET'])
@jwt_required()
def listar_movimientos():
    """Movimientos de la caja actual"""
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    if not caja:
        return jsonify({'movimientos': [], 'message': 'No hay caja abierta'}), 200

    movimientos = MovimientoCaja.query.filter_by(id_caja=caja.id_caja).order_by(
        MovimientoCaja.fecha_hora.desc()
    ).all()

    return jsonify({
        'movimientos': [m.to_dict() for m in movimientos],
        'caja': caja.to_dict(),
    }), 200


@caja_bp.route('/movimiento', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def registrar_movimiento():
    """Registrar movimiento manual (ingreso/egreso) en caja"""
    identity = get_current_identity()
    data = request.get_json()

    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    if not caja:
        return jsonify({'error': 'No hay caja abierta'}), 400

    tipo = data.get('tipo', '').upper()
    if tipo not in ('INGRESO', 'EGRESO'):
        return jsonify({'error': 'Tipo debe ser INGRESO o EGRESO'}), 400

    try:
        monto = float(data.get('monto', 0))
        if monto <= 0:
            return jsonify({'error': 'El monto debe ser positivo'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Monto inválido'}), 400

    concepto = data.get('concepto', '').strip()
    if not concepto:
        return jsonify({'error': 'Concepto requerido'}), 400

    metodo_pago = data.get('metodo_pago', 'EFECTIVO').strip() or 'EFECTIVO'

    mov = MovimientoCaja(
        id_caja=caja.id_caja,
        tipo=tipo,
        concepto=concepto,
        valor=monto,
        metodo_pago=metodo_pago,
        usuario=identity['usuario'],
        fecha_hora=datetime.utcnow(),
    )
    db.session.add(mov)

    if tipo == 'INGRESO':
        caja.total_ventas = (caja.total_ventas or 0) + monto
    else:
        caja.total_gastos = (caja.total_gastos or 0) + monto

    caja.monto_esperado = (caja.monto_inicial or 0) + (caja.total_ventas or 0) - (caja.total_gastos or 0)

    db.session.commit()

    return jsonify({
        'message': f'{tipo} registrado',
        'movimiento': mov.to_dict(),
        'caja': caja.to_dict(),
    }), 201


@caja_bp.route('/<int:id_caja>/movimientos', methods=['GET'])
@jwt_required()
def movimientos_caja(id_caja):
    """Movimientos de una caja específica"""
    movimientos = MovimientoCaja.query.filter_by(id_caja=id_caja).order_by(
        MovimientoCaja.fecha_hora.desc()
    ).all()

    return jsonify({
        'movimientos': [m.to_dict() for m in movimientos],
    }), 200


@caja_bp.route('/historial', methods=['GET'])
@jwt_required()
def historial_cajas():
    """Historial de cajas cerradas"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    paginated = CajaDiaria.query.filter_by(estado='CERRADA').order_by(
        CajaDiaria.fecha_apertura.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'cajas': [c.to_dict() for c in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
    }), 200
