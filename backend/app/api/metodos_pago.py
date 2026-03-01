"""
API de Métodos de Pago
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import MetodoPago
from app.utils.decorators import rol_requerido
from app.utils.validators import sanitize_string

metodos_pago_bp = Blueprint('metodos_pago', __name__)


@metodos_pago_bp.route('', methods=['GET'])
@jwt_required()
def listar_metodos():
    activos = request.args.get('activos', 'true') == 'true'
    query = MetodoPago.query
    if activos:
        query = query.filter(MetodoPago.activo == True)
    metodos = query.order_by(MetodoPago.nombre).all()
    return jsonify({'metodos': [m.to_dict() for m in metodos]}), 200


@metodos_pago_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def crear_metodo():
    data = request.get_json()
    nombre = sanitize_string(data.get('nombre', ''), 50).upper()
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    existente = MetodoPago.query.filter_by(nombre=nombre).first()
    if existente:
        return jsonify({'error': 'Ya existe ese método de pago'}), 409

    metodo = MetodoPago(nombre=nombre)
    db.session.add(metodo)
    db.session.commit()
    return jsonify({'message': 'Método creado', 'metodo': metodo.to_dict()}), 201


@metodos_pago_bp.route('/<int:id_metodo>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_metodo(id_metodo):
    metodo = MetodoPago.query.get_or_404(id_metodo)
    data = request.get_json()

    if 'nombre' in data:
        metodo.nombre = sanitize_string(data['nombre'], 50).upper()
    if 'activo' in data:
        metodo.activo = bool(data['activo'])

    db.session.commit()
    return jsonify({'message': 'Método actualizado', 'metodo': metodo.to_dict()}), 200
