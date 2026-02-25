"""
API de Colegios
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Colegio
from app.utils.decorators import rol_requerido
from app.utils.validators import sanitize_string

colegios_bp = Blueprint('colegios', __name__)


@colegios_bp.route('', methods=['GET'])
@jwt_required()
def listar_colegios():
    activos = request.args.get('activos', 'true') == 'true'
    query = Colegio.query
    if activos:
        query = query.filter(Colegio.activo == True)
    colegios = query.order_by(Colegio.nombre).all()
    return jsonify({'colegios': [c.to_dict() for c in colegios]}), 200


@colegios_bp.route('/<int:id_colegio>', methods=['GET'])
@jwt_required()
def obtener_colegio(id_colegio):
    colegio = Colegio.query.get_or_404(id_colegio)
    return jsonify({'colegio': colegio.to_dict()}), 200


@colegios_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def crear_colegio():
    data = request.get_json()
    nombre = sanitize_string(data.get('nombre', ''), 200)
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    existente = Colegio.query.filter_by(nombre=nombre).first()
    if existente:
        return jsonify({'error': 'Ya existe un colegio con ese nombre'}), 409

    colegio = Colegio(
        nombre=nombre,
        ciudad=sanitize_string(data.get('ciudad', 'Medellín'), 100),
    )
    db.session.add(colegio)
    db.session.commit()
    return jsonify({'message': 'Colegio creado', 'colegio': colegio.to_dict()}), 201


@colegios_bp.route('/<int:id_colegio>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_colegio(id_colegio):
    colegio = Colegio.query.get_or_404(id_colegio)
    data = request.get_json()

    if 'nombre' in data:
        colegio.nombre = sanitize_string(data['nombre'], 200)
    if 'ciudad' in data:
        colegio.ciudad = sanitize_string(data['ciudad'], 100)
    if 'activo' in data:
        colegio.activo = bool(data['activo'])

    db.session.commit()
    return jsonify({'message': 'Colegio actualizado', 'colegio': colegio.to_dict()}), 200
