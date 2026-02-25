"""
API de Stock Pendiente
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import StockPendiente, Stock
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity

pendientes_bp = Blueprint('pendientes', __name__)


@pendientes_bp.route('', methods=['GET'])
@jwt_required()
def listar_pendientes():
    """Listar items pendientes de entrega"""
    estado = request.args.get('estado', 'PENDIENTE')
    colegio_id = request.args.get('colegio_id', type=int)

    query = StockPendiente.query
    if estado:
        query = query.filter(StockPendiente.estado == estado)
    if colegio_id:
        query = query.filter(StockPendiente.id_colegio == colegio_id)

    pendientes = query.order_by(StockPendiente.fecha_registro.desc()).all()

    return jsonify({
        'pendientes': [p.to_dict() for p in pendientes],
        'total': len(pendientes),
    }), 200


@pendientes_bp.route('/<int:id_pendiente>/entregar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def entregar_pendiente(id_pendiente):
    """Marcar pendiente como entregado"""
    pendiente = StockPendiente.query.get_or_404(id_pendiente)
    identity = get_current_identity()

    if pendiente.estado != 'PENDIENTE':
        return jsonify({'error': 'Este pendiente ya fue procesado'}), 400

    pendiente.estado = 'ENTREGADO'
    db.session.commit()
    registrar_auditoria('stock_pendiente', id_pendiente, 'ENTREGAR', f'Pendiente entregado por {identity["usuario"]}')

    return jsonify({'message': 'Pendiente marcado como entregado', 'pendiente': pendiente.to_dict()}), 200
