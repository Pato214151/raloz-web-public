"""
API de Stock / Inventario
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Stock, Colegio, Producto
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('', methods=['GET'])
@jwt_required()
def listar_stock():
    """Listar stock con filtros"""
    colegio_id = request.args.get('colegio_id', type=int)
    producto_id = request.args.get('producto_id', type=int)
    solo_disponible = request.args.get('solo_disponible', 'false') == 'true'

    query = Stock.query

    if colegio_id:
        query = query.filter(Stock.id_colegio == colegio_id)
    if producto_id:
        query = query.filter(Stock.id_producto == producto_id)
    if solo_disponible:
        query = query.filter(Stock.cantidad > 0)

    stocks = query.order_by(Stock.id_producto, Stock.talla_individual).all()

    def stock_full(s):
        d = s.to_dict()
        d['producto_nombre'] = s.producto.nombre if s.producto else None
        d['colegio_nombre'] = s.colegio.nombre if s.colegio else None
        return d

    return jsonify({
        'stock': [stock_full(s) for s in stocks],
        'total_items': len(stocks),
    }), 200


@stock_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_stock():
    """Resumen de stock por colegio"""
    from sqlalchemy import func

    resumen = db.session.query(
        Stock.id_colegio,
        Colegio.nombre,
        func.sum(Stock.cantidad).label('total_unidades'),
        func.count(Stock.id_stock).label('total_items'),
    ).join(Colegio).group_by(Stock.id_colegio, Colegio.nombre).all()

    return jsonify({
        'resumen': [{
            'id_colegio': r.id_colegio,
            'colegio': r.nombre,
            'total_unidades': int(r.total_unidades or 0),
            'total_items': r.total_items,
        } for r in resumen]
    }), 200


@stock_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_stock():
    """Crear o actualizar registro de stock"""
    data = request.get_json()
    identity = get_current_identity()

    id_colegio = data.get('id_colegio')
    id_producto = data.get('id_producto')
    talla = data.get('talla_individual')
    cantidad = data.get('cantidad')

    if not all([id_colegio, id_producto, talla, cantidad is not None]):
        return jsonify({'error': 'Todos los campos son requeridos'}), 400

    try:
        cantidad = int(cantidad)
        if cantidad < 0:
            return jsonify({'error': 'La cantidad no puede ser negativa'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Cantidad inválida'}), 400

    stock = Stock.query.filter_by(
        id_colegio=id_colegio,
        id_producto=id_producto,
        talla_individual=talla,
    ).first()

    if stock:
        stock.cantidad = cantidad
    else:
        stock = Stock(
            id_colegio=id_colegio,
            id_producto=id_producto,
            talla_individual=talla,
            cantidad=cantidad,
        )
        db.session.add(stock)

    db.session.commit()
    registrar_auditoria('stock', stock.id_stock, 'ACTUALIZAR', f'Stock: {cantidad} uds')

    return jsonify({'message': 'Stock actualizado', 'stock': stock.to_dict()}), 200


@stock_bp.route('/<int:id_stock>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def editar_stock(id_stock):
    """Editar cantidad de un registro de stock"""
    stock = Stock.query.get_or_404(id_stock)
    data = request.get_json()

    if 'cantidad' in data:
        try:
            cantidad = int(data['cantidad'])
            if cantidad < 0:
                return jsonify({'error': 'La cantidad no puede ser negativa'}), 400
            stock.cantidad = cantidad
        except (ValueError, TypeError):
            return jsonify({'error': 'Cantidad inválida'}), 400

    db.session.commit()
    registrar_auditoria('stock', id_stock, 'EDITAR', f'Stock editado: {stock.cantidad} uds')

    return jsonify({'message': 'Stock actualizado', 'stock': stock.to_dict()}), 200


@stock_bp.route('/<int:id_stock>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_stock(id_stock):
    """Eliminar un registro de stock"""
    stock = Stock.query.get_or_404(id_stock)
    db.session.delete(stock)
    db.session.commit()
    registrar_auditoria('stock', id_stock, 'ELIMINAR', 'Stock eliminado')

    return jsonify({'message': 'Stock eliminado'}), 200


@stock_bp.route('/masivo', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_stock_masivo():
    """Actualizar múltiples items de stock"""
    data = request.get_json()
    items = data.get('items', [])

    if not items:
        return jsonify({'error': 'No hay items para actualizar'}), 400

    actualizados = 0
    for item in items:
        stock = Stock.query.filter_by(
            id_colegio=item['id_colegio'],
            id_producto=item['id_producto'],
            talla_individual=item['talla_individual'],
        ).first()

        cantidad = int(item.get('cantidad', 0))

        if stock:
            stock.cantidad = cantidad
        else:
            stock = Stock(
                id_colegio=item['id_colegio'],
                id_producto=item['id_producto'],
                talla_individual=item['talla_individual'],
                cantidad=cantidad,
            )
            db.session.add(stock)
        actualizados += 1

    db.session.commit()
    return jsonify({'message': f'{actualizados} items actualizados'}), 200
