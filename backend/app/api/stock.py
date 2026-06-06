"""
API de Stock / Inventario
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload
from app import db
from app.models import Stock, Colegio, Producto, MovimientoInventario
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.inventario import registrar_movimiento, construir_catalogo_colegio

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('', methods=['GET'])
@jwt_required()
def listar_stock():
    """Listar stock con filtros"""
    colegio_id = request.args.get('colegio_id', type=int)
    producto_id = request.args.get('producto_id', type=int)
    solo_disponible = request.args.get('solo_disponible', 'false') == 'true'

    query = Stock.query.options(
        joinedload(Stock.producto),
        joinedload(Stock.colegio),
    )

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
        d['producto_tipo'] = s.producto.tipo if s.producto else None
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


@stock_bp.route('/actividad', methods=['GET'])
@jwt_required()
def actividad_stock():
    """Actividad/log de movimientos de stock"""
    from app.models.auditoria import Auditoria
    usuario_filtro = request.args.get('usuario', '').strip()
    limit = min(request.args.get('limit', 200, type=int), 500)

    query = Auditoria.query.filter_by(tabla_afectada='stock')
    if usuario_filtro:
        query = query.filter(Auditoria.usuario == usuario_filtro)

    registros = query.order_by(Auditoria.fecha_hora.desc()).limit(limit).all()

    # Usuarios únicos para filtro
    todos_usuarios = db.session.query(Auditoria.usuario).filter_by(
        tabla_afectada='stock'
    ).distinct().all()

    return jsonify({
        'actividad': [r.to_dict() for r in registros],
        'usuarios': [u[0] for u in todos_usuarios],
    }), 200


@stock_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def actualizar_stock():
    """Crear o actualizar registro de stock"""
    data = request.get_json()
    identity = get_current_identity()

    try:
        id_colegio = int(data.get('id_colegio'))
        id_producto = int(data.get('id_producto'))
    except (ValueError, TypeError):
        return jsonify({'error': 'id_colegio e id_producto deben ser números'}), 400

    talla = (data.get('talla_individual') or '').strip()
    cantidad = data.get('cantidad')
    observaciones = (data.get('observaciones') or '').strip()

    if not all([id_colegio, id_producto, talla, cantidad is not None]):
        return jsonify({'error': 'Todos los campos son requeridos'}), 400

    try:
        cantidad = int(cantidad)
        if cantidad < 0:
            return jsonify({'error': 'La cantidad no puede ser negativa'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Cantidad inválida'}), 400

    producto = Producto.query.get(id_producto)
    colegio = Colegio.query.get(id_colegio)
    prod_nombre = producto.nombre if producto else f'Prod#{id_producto}'
    col_nombre = colegio.nombre if colegio else f'Col#{id_colegio}'

    # AJUSTE: fija el stock en `cantidad` y lo deja en el kardex
    stock, _mov = registrar_movimiento(
        id_colegio, id_producto, talla, 'AJUSTE', cantidad,
        usuario=identity['usuario'],
        motivo='Ajuste manual' + (f' — {observaciones}' if observaciones else ''),
    )
    db.session.commit()

    comentario = f'{prod_nombre} | Talla {talla} | {col_nombre} | ajustado a {cantidad} uds'
    if observaciones:
        comentario += f' | Obs: {observaciones}'
    registrar_auditoria('stock', stock.id_stock, 'ACTUALIZAR', comentario)

    d = stock.to_dict()
    d['producto_nombre'] = prod_nombre
    d['colegio_nombre'] = col_nombre
    return jsonify({'message': 'Stock actualizado', 'stock': d}), 200


@stock_bp.route('/<int:id_stock>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def editar_stock(id_stock):
    """Editar cantidad de un registro de stock"""
    stock = Stock.query.get_or_404(id_stock)
    data = request.get_json()

    cantidad_anterior = stock.cantidad
    observaciones = (data.get('observaciones') or '').strip()

    if 'cantidad' in data:
        try:
            cantidad = int(data['cantidad'])
            if cantidad < 0:
                return jsonify({'error': 'La cantidad no puede ser negativa'}), 400
            stock.cantidad = cantidad
        except (ValueError, TypeError):
            return jsonify({'error': 'Cantidad inválida'}), 400

    db.session.commit()

    prod_nombre = stock.producto.nombre if stock.producto else f'Prod#{stock.id_producto}'
    col_nombre = stock.colegio.nombre if stock.colegio else f'Col#{stock.id_colegio}'
    comentario = f'{prod_nombre} | Talla {stock.talla_individual} | {col_nombre} | {cantidad_anterior}→{stock.cantidad} uds'
    if observaciones:
        comentario += f' | Obs: {observaciones}'
    registrar_auditoria('stock', id_stock, 'EDITAR', comentario)

    d = stock.to_dict()
    d['producto_nombre'] = prod_nombre
    d['colegio_nombre'] = col_nombre
    return jsonify({'message': 'Stock actualizado', 'stock': d}), 200


@stock_bp.route('/<int:id_stock>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def eliminar_stock(id_stock):
    """Eliminar un registro de stock"""
    stock = Stock.query.get_or_404(id_stock)
    prod_nombre = stock.producto.nombre if stock.producto else f'Prod#{stock.id_producto}'
    col_nombre = stock.colegio.nombre if stock.colegio else f'Col#{stock.id_colegio}'
    comentario = f'{prod_nombre} | Talla {stock.talla_individual} | {col_nombre} | Eliminado ({stock.cantidad} uds)'

    db.session.delete(stock)
    db.session.commit()
    registrar_auditoria('stock', id_stock, 'ELIMINAR', comentario)

    return jsonify({'message': 'Stock eliminado'}), 200


@stock_bp.route('/masivo', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
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


@stock_bp.route('/entrada', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def registrar_entrada():
    """Registra una ENTRADA de mercancía: SUMA al stock (no reemplaza) y deja kardex."""
    data = request.get_json() or {}
    identity = get_current_identity()

    try:
        id_colegio = int(data.get('id_colegio'))
        id_producto = int(data.get('id_producto'))
        cantidad = int(data.get('cantidad'))
    except (ValueError, TypeError):
        return jsonify({'error': 'id_colegio, id_producto y cantidad deben ser números'}), 400

    talla = (data.get('talla_individual') or '').strip()
    motivo = (data.get('motivo') or 'Recepción de mercancía').strip()

    if not all([id_colegio, id_producto, talla]) or cantidad <= 0:
        return jsonify({'error': 'Datos incompletos o cantidad inválida (debe ser > 0)'}), 400

    producto = Producto.query.get(id_producto)
    colegio = Colegio.query.get(id_colegio)
    if not producto or not colegio:
        return jsonify({'error': 'Producto o colegio no encontrado'}), 404

    stock, _mov = registrar_movimiento(
        id_colegio, id_producto, talla, 'ENTRADA', cantidad,
        usuario=identity['usuario'], motivo=motivo,
    )
    db.session.commit()

    registrar_auditoria('stock', stock.id_stock, 'ENTRADA',
                        f'{producto.nombre} | Talla {talla} | {colegio.nombre} | '
                        f'+{cantidad} uds (total {stock.cantidad})')

    d = stock.to_dict()
    d['producto_nombre'] = producto.nombre
    d['colegio_nombre'] = colegio.nombre
    return jsonify({'message': f'Entrada registrada: +{cantidad}', 'stock': d}), 200


@stock_bp.route('/movimientos', methods=['GET'])
@jwt_required()
def listar_movimientos_inventario():
    """Kardex: historial de movimientos de inventario (entradas/salidas/ajustes)."""
    colegio_id = request.args.get('colegio_id', type=int)
    producto_id = request.args.get('producto_id', type=int)
    talla = request.args.get('talla', type=str)
    tipo = request.args.get('tipo', type=str)
    limite = min(request.args.get('limite', default=200, type=int), 1000)

    q = MovimientoInventario.query
    if colegio_id:
        q = q.filter(MovimientoInventario.id_colegio == colegio_id)
    if producto_id:
        q = q.filter(MovimientoInventario.id_producto == producto_id)
    if talla:
        q = q.filter(MovimientoInventario.talla_individual == talla)
    if tipo:
        q = q.filter(MovimientoInventario.tipo == tipo.upper())

    movs = q.order_by(MovimientoInventario.fecha.desc()).limit(limite).all()

    prod_ids = {m.id_producto for m in movs}
    col_ids = {m.id_colegio for m in movs}
    prods = {p.id_producto: p.nombre for p in Producto.query.filter(Producto.id_producto.in_(prod_ids)).all()} if prod_ids else {}
    cols = {c.id_colegio: c.nombre for c in Colegio.query.filter(Colegio.id_colegio.in_(col_ids)).all()} if col_ids else {}

    resultado = []
    for m in movs:
        d = m.to_dict()
        d['producto_nombre'] = prods.get(m.id_producto)
        d['colegio_nombre'] = cols.get(m.id_colegio)
        resultado.append(d)

    return jsonify({'movimientos': resultado}), 200


@stock_bp.route('/catalogo', methods=['GET'])
@jwt_required()
def catalogo_colegio():
    """
    Catálogo COMPLETO de un colegio: todas las prendas que vende (según
    precios_colegio) con su stock por talla — INCLUIDAS las que están en 0.
    Así se ve todo lo del colegio, no solo lo que tiene existencias.
    """
    colegio_id = request.args.get('colegio_id', type=int)
    if not colegio_id:
        return jsonify({'error': 'colegio_id requerido'}), 400
    colegio = Colegio.query.get(colegio_id)
    if not colegio:
        return jsonify({'error': 'Colegio no encontrado'}), 404

    catalogo = construir_catalogo_colegio(colegio_id)

    return jsonify({
        'colegio': colegio.nombre,
        'id_colegio': colegio_id,
        'catalogo': catalogo,
        'total_unidades': sum(c['total'] for c in catalogo),
    }), 200
