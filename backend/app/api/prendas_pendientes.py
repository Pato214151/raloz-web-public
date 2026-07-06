"""
API de Prendas Pendientes de Entrega
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import PrendaPendiente, Factura
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from datetime import date

prendas_bp = Blueprint('prendas', __name__)


@prendas_bp.route('', methods=['GET'])
@jwt_required()
def listar_prendas():
    """Listar prendas pendientes"""
    estado = request.args.get('estado', '')
    colegio_id = request.args.get('colegio_id', type=int)
    buscar = request.args.get('buscar', '').strip()

    query = PrendaPendiente.query

    if estado:
        query = query.filter(PrendaPendiente.estado == estado)
    if colegio_id:
        query = query.filter(PrendaPendiente.id_colegio == colegio_id)
    if buscar:
        buscar_like = f'%{buscar}%'
        query = query.filter(
            db.or_(
                PrendaPendiente.cliente_nombre.ilike(buscar_like),
                PrendaPendiente.producto_nombre.ilike(buscar_like),
                PrendaPendiente.numero_factura.ilike(buscar_like),
            )
        )

    prendas = query.order_by(PrendaPendiente.fecha_registro.desc()).all()

    return jsonify({
        'prendas': [p.to_dict() for p in prendas],
        'total': len(prendas),
        'pendientes': len([p for p in prendas if p.estado == 'PENDIENTE']),
    }), 200


@prendas_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def crear_prenda():
    """Crear prenda pendiente"""
    data = request.get_json()
    identity = get_current_identity()

    required = ['id_factura', 'producto_nombre', 'cantidad']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Campo {field} requerido'}), 400

    # Obtener info de la factura
    factura = Factura.query.get(data['id_factura'])
    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    prenda = PrendaPendiente(
        id_factura=data['id_factura'],
        numero_factura=factura.numero_factura,
        id_colegio=factura.id_colegio,
        colegio_nombre=factura.colegio.nombre if factura.colegio else None,
        cliente_nombre=factura.cliente_nombre or data.get('cliente_nombre', ''),
        producto_nombre=data['producto_nombre'],
        talla=data.get('talla', ''),
        cantidad=data['cantidad'],
        genero=data.get('genero', 'NIÑO'),
        estado='PENDIENTE',
        fecha_registro=date.today(),
        fecha_factura=factura.fecha_factura,
        observaciones=data.get('observaciones', ''),
        usuario_registro=identity['usuario'],
    )

    db.session.add(prenda)
    db.session.commit()
    registrar_auditoria('prendas_pendientes', prenda.id_pendiente, 'CREAR',
                        f'Prenda pendiente creada por {identity["usuario"]}')

    return jsonify({'message': 'Prenda pendiente creada', 'prenda': prenda.to_dict()}), 201


@prendas_bp.route('/<int:id_pendiente>/entregar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def entregar_prenda(id_pendiente):
    """Marcar prenda como entregada"""
    prenda = PrendaPendiente.query.get_or_404(id_pendiente)
    identity = get_current_identity()

    if prenda.estado != 'PENDIENTE':
        return jsonify({'error': 'Esta prenda ya fue procesada'}), 400

    prenda.estado = 'ENTREGADO'
    prenda.fecha_entrega = date.today()
    db.session.commit()
    registrar_auditoria('prendas_pendientes', id_pendiente, 'ENTREGAR',
                        f'Prenda entregada por {identity["usuario"]}')

    return jsonify({'message': 'Prenda marcada como entregada', 'prenda': prenda.to_dict()}), 200


@prendas_bp.route('/entregar-batch', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def entregar_prendas_batch():
    """Marcar varias prendas como entregadas de una vez (botón de entrega
    masiva del panel). Solo procesa las que siguen PENDIENTES."""
    data = request.get_json() or {}
    ids = data.get('ids')
    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'ids requerido (lista de prendas)'}), 400
    try:
        ids = [int(x) for x in ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'ids inválidos'}), 400

    identity = get_current_identity()
    prendas = PrendaPendiente.query.filter(
        PrendaPendiente.id_pendiente.in_(ids),
        PrendaPendiente.estado == 'PENDIENTE',
    ).all()

    for prenda in prendas:
        prenda.estado = 'ENTREGADO'
        prenda.fecha_entrega = date.today()
    db.session.commit()

    if prendas:
        registrar_auditoria('prendas_pendientes', prendas[0].id_pendiente, 'ENTREGAR_BATCH',
                            f'{len(prendas)} prendas entregadas por {identity["usuario"]}')

    return jsonify({
        'message': f'{len(prendas)} prenda(s) marcada(s) como entregada(s)',
        'entregadas': len(prendas),
        'omitidas': len(ids) - len(prendas),
    }), 200


@prendas_bp.route('/<int:id_pendiente>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def actualizar_prenda(id_pendiente):
    """Actualizar prenda pendiente"""
    prenda = PrendaPendiente.query.get_or_404(id_pendiente)
    data = request.get_json()

    for field in ['producto_nombre', 'talla', 'cantidad', 'genero', 'observaciones']:
        if field in data:
            setattr(prenda, field, data[field])

    db.session.commit()
    return jsonify({'message': 'Prenda actualizada', 'prenda': prenda.to_dict()}), 200


@prendas_bp.route('/<int:id_pendiente>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_prenda(id_pendiente):
    """Eliminar prenda pendiente"""
    prenda = PrendaPendiente.query.get_or_404(id_pendiente)
    identity = get_current_identity()

    db.session.delete(prenda)
    db.session.commit()
    registrar_auditoria('prendas_pendientes', id_pendiente, 'ELIMINAR',
                        f'Prenda eliminada por {identity["usuario"]}')

    return jsonify({'message': 'Prenda eliminada'}), 200
