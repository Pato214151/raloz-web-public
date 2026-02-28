"""
API de Clientes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Cliente
from app.utils.decorators import rol_requerido
from app.utils.validators import sanitize_string, validate_email, validate_phone

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('', methods=['GET'])
@jwt_required()
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    buscar = request.args.get('buscar', '').strip()
    colegio_id = request.args.get('colegio_id', type=int)

    query = Cliente.query.filter(Cliente.activo == True)

    if buscar:
        like = f'%{buscar}%'
        query = query.filter(
            (Cliente.nombre.ilike(like)) |
            (Cliente.telefono.ilike(like)) |
            (Cliente.numero_documento.ilike(like))
        )
    if colegio_id:
        query = query.filter(Cliente.id_colegio == colegio_id)

    paginated = query.order_by(Cliente.nombre).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'clientes': [c.to_dict() for c in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
    }), 200


@clientes_bp.route('', methods=['POST'])
@jwt_required()
def crear_cliente():
    data = request.get_json()
    nombre = sanitize_string(data.get('nombre', ''), 200)
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    telefono = sanitize_string(data.get('telefono', ''), 50)
    if telefono and not validate_phone(telefono):
        return jsonify({'error': 'Formato de teléfono inválido'}), 400

    email = sanitize_string(data.get('email', ''), 255)
    if email and not validate_email(email):
        return jsonify({'error': 'Formato de email inválido'}), 400

    cliente = Cliente(
        tipo_documento=sanitize_string(data.get('tipo_documento', 'CC'), 10),
        numero_documento=sanitize_string(data.get('numero_documento', ''), 50),
        nombre=nombre,
        telefono=telefono,
        email=email,
        direccion=sanitize_string(data.get('direccion', ''), 500),
        id_colegio=data.get('id_colegio'),
        notas=sanitize_string(data.get('notas', ''), 1000),
    )
    db.session.add(cliente)
    db.session.commit()
    return jsonify({'message': 'Cliente creado', 'cliente': cliente.to_dict()}), 201


@clientes_bp.route('/<int:id_cliente>', methods=['PUT'])
@jwt_required()
def actualizar_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    data = request.get_json()

    if 'nombre' in data:
        cliente.nombre = sanitize_string(data['nombre'], 200)
    if 'telefono' in data:
        cliente.telefono = sanitize_string(data['telefono'], 50)
    if 'email' in data:
        cliente.email = sanitize_string(data['email'], 255)
    if 'direccion' in data:
        cliente.direccion = sanitize_string(data['direccion'], 500)
    if 'id_colegio' in data:
        cliente.id_colegio = data['id_colegio']
    if 'notas' in data:
        cliente.notas = sanitize_string(data['notas'], 1000)

    db.session.commit()
    return jsonify({'message': 'Cliente actualizado', 'cliente': cliente.to_dict()}), 200
