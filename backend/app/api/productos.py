"""
API de Productos
"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Producto, PrecioColegio
from app.utils.decorators import rol_requerido
from app.utils.validators import sanitize_string

productos_bp = Blueprint('productos', __name__)


@productos_bp.route('', methods=['GET'])
@jwt_required()
def listar_productos():
    """Listar todos los productos activos"""
    activos = request.args.get('activos', 'true') == 'true'
    query = Producto.query
    if activos:
        query = query.filter(Producto.activo == True)
    productos = query.order_by(Producto.nombre).all()
    return jsonify({'productos': [p.to_dict() for p in productos]}), 200


@productos_bp.route('/<int:id_producto>', methods=['GET'])
@jwt_required()
def obtener_producto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    return jsonify({'producto': producto.to_dict()}), 200


@productos_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def crear_producto():
    data = request.get_json()
    nombre = sanitize_string(data.get('nombre', ''), 200)
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    producto = Producto(
        codigo=sanitize_string(data.get('codigo', ''), 50),
        nombre=nombre,
        tipo=sanitize_string(data.get('tipo', ''), 100),
    )
    db.session.add(producto)
    db.session.commit()
    return jsonify({'message': 'Producto creado', 'producto': producto.to_dict()}), 201


@productos_bp.route('/<int:id_producto>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_producto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    data = request.get_json()

    if 'nombre' in data:
        producto.nombre = sanitize_string(data['nombre'], 200)
    if 'codigo' in data:
        producto.codigo = sanitize_string(data['codigo'], 50)
    if 'tipo' in data:
        producto.tipo = sanitize_string(data['tipo'], 100)
    if 'activo' in data:
        producto.activo = bool(data['activo'])
    if 'destacado' in data:
        producto.destacado = bool(data['destacado'])
    if 'orden' in data:
        try:
            producto.orden = int(data['orden'])
        except (TypeError, ValueError):
            pass
    # Programación por fecha (ISO 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM'); vacío = quitar
    for campo in ('publicar_desde', 'publicar_hasta'):
        if campo in data:
            val = data[campo]
            if not val:
                setattr(producto, campo, None)
            else:
                try:
                    setattr(producto, campo, datetime.fromisoformat(str(val).replace('Z', '')))
                except ValueError:
                    pass

    db.session.commit()
    return jsonify({'message': 'Producto actualizado', 'producto': producto.to_dict()}), 200


@productos_bp.route('/precios', methods=['GET'])
@jwt_required()
def listar_precios():
    """Listar precios por colegio"""
    colegio_id = request.args.get('colegio_id', type=int)
    query = PrecioColegio.query
    if colegio_id:
        query = query.filter(PrecioColegio.id_colegio == colegio_id)
    precios = query.all()
    return jsonify({'precios': [p.to_dict() for p in precios]}), 200


@productos_bp.route('/precios', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def guardar_precio():
    """Crear o actualizar precio"""
    data = request.get_json()
    id_colegio = data.get('id_colegio')
    id_producto = data.get('id_producto')
    talla_grupo = sanitize_string(data.get('talla_grupo', ''), 50)
    precio = data.get('precio_unitario')

    if not all([id_colegio, id_producto, talla_grupo, precio]):
        return jsonify({'error': 'Todos los campos requeridos'}), 400

    existente = PrecioColegio.query.filter_by(
        id_colegio=id_colegio, id_producto=id_producto, talla_grupo=talla_grupo
    ).first()

    if existente:
        existente.precio_unitario = float(precio)
    else:
        nuevo = PrecioColegio(
            id_colegio=id_colegio, id_producto=id_producto,
            talla_grupo=talla_grupo, precio_unitario=float(precio)
        )
        db.session.add(nuevo)

    db.session.commit()
    return jsonify({'message': 'Precio guardado'}), 200
