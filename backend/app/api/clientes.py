"""
API de Clientes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Cliente, Factura
from app.utils.decorators import rol_requerido
from app.utils.validators import sanitize_string, validate_email, validate_phone
from datetime import datetime

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
            (Cliente.numero_documento.ilike(like)) |
            (Cliente.email.ilike(like))
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
        apellidos=sanitize_string(data.get('apellidos', ''), 200),
        razon_social=sanitize_string(data.get('razon_social', ''), 300),
        telefono=telefono,
        celular=sanitize_string(data.get('celular', ''), 50),
        email=email,
        direccion=sanitize_string(data.get('direccion', ''), 500),
        ciudad=sanitize_string(data.get('ciudad', ''), 100),
        departamento=sanitize_string(data.get('departamento', ''), 100),
        codigo_postal=sanitize_string(data.get('codigo_postal', ''), 20),
        pais=sanitize_string(data.get('pais', 'Colombia'), 50),
        dv=sanitize_string(data.get('dv', ''), 5),
        id_colegio=data.get('id_colegio') or None,
        estudiante_nombre=sanitize_string(data.get('estudiante_nombre', ''), 200),
        estudiante_grado=sanitize_string(data.get('estudiante_grado', ''), 50),
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

    campos_texto = {
        'nombre': 200, 'apellidos': 200, 'razon_social': 300,
        'telefono': 50, 'celular': 50, 'email': 255,
        'direccion': 500, 'ciudad': 100, 'departamento': 100,
        'codigo_postal': 20, 'pais': 50, 'dv': 5,
        'numero_documento': 50,
        'estudiante_nombre': 200, 'estudiante_grado': 50,
        'notas': 1000, 'tipo_documento': 10,
    }

    for campo, max_len in campos_texto.items():
        if campo in data:
            setattr(cliente, campo, sanitize_string(data[campo], max_len))

    if 'id_colegio' in data:
        cliente.id_colegio = data['id_colegio'] or None

    cliente.fecha_actualizacion = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': 'Cliente actualizado', 'cliente': cliente.to_dict()}), 200


@clientes_bp.route('/<int:id_cliente>', methods=['DELETE'])
@jwt_required()
def eliminar_cliente(id_cliente):
    """Desactivar cliente (soft delete)"""
    cliente = Cliente.query.get_or_404(id_cliente)
    cliente.activo = False
    cliente.fecha_actualizacion = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Cliente eliminado'}), 200


@clientes_bp.route('/<int:id_cliente>/historial', methods=['GET'])
@jwt_required()
def historial_cliente(id_cliente):
    """Historial de compras de un cliente"""
    cliente = Cliente.query.get_or_404(id_cliente)

    facturas = Factura.query.filter(
        Factura.cliente_nombre == cliente.nombre
    ).order_by(Factura.fecha_factura.desc()).limit(50).all()

    total_compras = sum(f.total for f in facturas)
    total_pagado = sum(f.total_abonado or 0 for f in facturas)

    return jsonify({
        'cliente': cliente.to_dict(),
        'facturas': [{
            'id_factura': f.id_factura,
            'numero_factura': f.numero_factura,
            'fecha': f.fecha_factura.isoformat() if f.fecha_factura else None,
            'total': f.total,
            'total_abonado': f.total_abonado or 0,
            'saldo_pendiente': f.saldo_pendiente or 0,
            'estado': f.estado,
            'colegio_nombre': f.colegio.nombre if f.colegio else None,
            'detalles': [{
                'producto_nombre': d.producto.nombre if d.producto else '—',
                'talla': d.talla_individual,
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'total_linea': d.total_linea,
            } for d in f.detalles],
        } for f in facturas],
        'resumen': {
            'total_facturas': len(facturas),
            'total_compras': total_compras,
            'total_pagado': total_pagado,
            'saldo_pendiente': total_compras - total_pagado,
        }
    }), 200
