"""
API Pública — Sin autenticación
Para consumo desde la página web (ralozcol.netlify.app)
"""

from flask import Blueprint, request, jsonify
from app import db
from app.models import Factura, FacturaDetalle, Stock, StockPendiente
from app.models.colegio import Colegio
from app.models.producto import Producto
from app.models.precio_colegio import PrecioColegio
from app.utils.validators import sanitize_string
from datetime import date, datetime

public_bp = Blueprint('public', __name__)


@public_bp.route('/colegios', methods=['GET'])
def get_colegios_publico():
    """Lista colegios activos para mostrar en la página web"""
    colegios = Colegio.query.filter_by(activo=True).order_by(Colegio.nombre).all()
    return jsonify({
        'colegios': [
            {'id_colegio': c.id_colegio, 'nombre': c.nombre, 'ciudad': c.ciudad}
            for c in colegios
        ]
    }), 200


@public_bp.route('/catalogo', methods=['GET'])
def get_catalogo_publico():
    """
    Retorna productos + precios + disponibilidad para un colegio.
    Query param: colegio_id (requerido)
    """
    colegio_id = request.args.get('colegio_id', type=int)
    if not colegio_id:
        return jsonify({'error': 'colegio_id requerido'}), 400

    colegio = Colegio.query.filter_by(id_colegio=colegio_id, activo=True).first()
    if not colegio:
        return jsonify({'error': 'Colegio no encontrado'}), 404

    # Precios por colegio
    precios = PrecioColegio.query.filter_by(id_colegio=colegio_id).all()
    precios_map = {}
    for p in precios:
        if p.id_producto not in precios_map:
            precios_map[p.id_producto] = {}
        precios_map[p.id_producto][p.talla_grupo] = p.precio_unitario

    # Stock disponible por colegio
    stock_items = Stock.query.filter_by(id_colegio=colegio_id).filter(Stock.cantidad > 0).all()
    stock_map = {}
    for s in stock_items:
        if s.id_producto not in stock_map:
            stock_map[s.id_producto] = {}
        stock_map[s.id_producto][s.talla_individual] = s.cantidad

    # Productos con precio en este colegio
    ids_con_precio = list(precios_map.keys())
    productos = Producto.query.filter(
        Producto.id_producto.in_(ids_con_precio),
        Producto.activo == True
    ).order_by(Producto.nombre).all()

    catalogo = []
    for prod in productos:
        precios_prod = precios_map.get(prod.id_producto, {})
        stock_prod = stock_map.get(prod.id_producto, {})
        precio_minimo = min(precios_prod.values()) if precios_prod else 0
        catalogo.append({
            'id_producto': prod.id_producto,
            'codigo': prod.codigo,
            'nombre': prod.nombre,
            'tipo': prod.tipo,
            'precio_minimo': precio_minimo,
            'precios': precios_prod,
            'stock': stock_prod,
            'tiene_stock': len(stock_prod) > 0,
        })

    return jsonify({
        'colegio': {'id_colegio': colegio.id_colegio, 'nombre': colegio.nombre},
        'catalogo': catalogo,
    }), 200


@public_bp.route('/pedido', methods=['POST'])
def crear_pedido_web():
    """
    Recibe un pedido desde la página web y lo registra como factura con canal='WEB'.
    No requiere autenticación.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    # Validar campos obligatorios
    if not data.get('cliente_nombre') or not data.get('id_colegio'):
        return jsonify({'error': 'Nombre del cliente y colegio son obligatorios'}), 400

    detalles = data.get('detalles', [])
    if not detalles:
        return jsonify({'error': 'El pedido debe tener al menos un producto'}), 400

    try:
        # Generar número de factura web
        hoy = date.today()
        prefijo = f'WEB{hoy.strftime("%y%m%d")}'
        ultima = Factura.query.filter(
            Factura.numero_factura.like(f'{prefijo}%')
        ).order_by(Factura.id_factura.desc()).first()
        if ultima:
            try:
                consecutivo = int(ultima.numero_factura.replace(prefijo, '')) + 1
            except Exception:
                consecutivo = 1
        else:
            consecutivo = 1
        numero = f'{prefijo}{consecutivo:03d}'

        # Calcular total
        total = 0
        for item in detalles:
            cantidad = int(item.get('cantidad', 0))
            precio = float(item.get('precio_unitario', 0))
            if cantidad <= 0 or precio <= 0:
                return jsonify({'error': 'Cantidad y precio deben ser positivos'}), 400
            total += cantidad * precio

        domicilio = float(data.get('domicilio', 0))
        total_con_domicilio = total + domicilio

        # Crear factura
        factura = Factura(
            numero_factura=numero,
            id_colegio=int(data['id_colegio']),
            cliente_nombre=sanitize_string(data['cliente_nombre'], 200),
            cliente_telefono=sanitize_string(data.get('cliente_telefono', ''), 50),
            cliente_email=sanitize_string(data.get('cliente_email', ''), 255),
            cliente_direccion=sanitize_string(data.get('cliente_direccion', ''), 500),
            fecha_factura=hoy,
            total=total_con_domicilio,
            subtotal=total,
            domicilio=domicilio,
            total_abonado=0,
            saldo_pendiente=total_con_domicilio,
            estado='PENDIENTE',
            estado_entrega='POR_ENTREGAR',
            metodo_pago=data.get('metodo_pago', 'PENDIENTE'),
            observaciones=sanitize_string(data.get('observaciones', 'Pedido desde página web'), 500),
            usuario_creacion='WEB',
            canal='WEB',
        )
        db.session.add(factura)
        db.session.flush()

        # Crear detalles y descontar stock
        for item in detalles:
            cantidad = int(item['cantidad'])
            precio = float(item['precio_unitario'])
            talla = sanitize_string(item.get('talla_individual', ''), 20)
            id_prod = int(item['id_producto'])

            detalle = FacturaDetalle(
                id_factura=factura.id_factura,
                id_producto=id_prod,
                talla_individual=talla,
                cantidad=cantidad,
                precio_unitario=precio,
                total_linea=cantidad * precio,
            )
            db.session.add(detalle)

            # Descontar stock si hay disponible
            stock = Stock.query.filter_by(
                id_colegio=factura.id_colegio,
                id_producto=id_prod,
                talla_individual=talla,
            ).first()
            if stock and stock.cantidad >= cantidad:
                stock.cantidad -= cantidad
            elif stock:
                faltante = cantidad - stock.cantidad
                stock.cantidad = 0
                db.session.add(StockPendiente(
                    id_factura=factura.id_factura,
                    id_colegio=factura.id_colegio,
                    id_producto=id_prod,
                    talla_individual=talla,
                    cantidad_faltante=faltante,
                ))
            else:
                db.session.add(StockPendiente(
                    id_factura=factura.id_factura,
                    id_colegio=factura.id_colegio,
                    id_producto=id_prod,
                    talla_individual=talla,
                    cantidad_faltante=cantidad,
                ))

        db.session.commit()

        return jsonify({
            'message': 'Pedido registrado exitosamente',
            'numero_pedido': numero,
            'total': total_con_domicilio,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al registrar el pedido'}), 500


@public_bp.route('/pedido/<numero>', methods=['GET'])
def consultar_pedido_web(numero):
    """Permite al cliente consultar el estado de su pedido por número"""
    factura = Factura.query.filter_by(numero_factura=numero.upper()).first()
    if not factura:
        return jsonify({'error': 'Pedido no encontrado'}), 404

    return jsonify({
        'numero_pedido': factura.numero_factura,
        'estado': factura.estado,
        'estado_entrega': factura.estado_entrega,
        'total': factura.total,
        'saldo_pendiente': factura.saldo_pendiente,
        'fecha': factura.fecha_factura.isoformat() if factura.fecha_factura else None,
        'cliente_nombre': factura.cliente_nombre,
        'productos': [
            {
                'nombre': d.producto.nombre if d.producto else 'Producto',
                'talla': d.talla_individual,
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'total': d.total_linea,
            }
            for d in factura.detalles
        ],
    }), 200
