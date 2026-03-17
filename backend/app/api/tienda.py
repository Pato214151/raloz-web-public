"""
API Pública de Tienda Online — RALOZ COL SAS
Endpoints sin autenticación para la página web de Netlify
Pagos procesados por MercadoPago (persona natural)
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime, date, timedelta
from sqlalchemy import func
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
from app import db
from app.utils.email_service import enviar_email_factura
from app.models import (
    Colegio, Producto, PrecioColegio, Stock,
    PedidoWeb, Factura, FacturaDetalle, Pago,
    SerieFacturacion, MetodoPago, Cliente, Reserva
)

tienda_bp = Blueprint('tienda', __name__)

MP_API = 'https://api.mercadopago.com'


# ══════════════════════════════════════════════════════════════
# COLEGIOS — catálogo público
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/colegios', methods=['GET'])
def listar_colegios():
    """Retorna colegios activos que tienen productos con precio y stock"""
    colegios = Colegio.query.filter_by(activo=True).order_by(Colegio.nombre).all()
    resultado = []
    for c in colegios:
        tiene_productos = PrecioColegio.query.filter_by(id_colegio=c.id_colegio).first()
        if tiene_productos:
            resultado.append({'id_colegio': c.id_colegio, 'nombre': c.nombre, 'ciudad': c.ciudad})
    return jsonify({'colegios': resultado}), 200


# ══════════════════════════════════════════════════════════════
# CATÁLOGO — productos por colegio con precios y stock
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/catalogo/<int:id_colegio>', methods=['GET'])
def catalogo_colegio(id_colegio):
    """Retorna productos disponibles (con stock > 0) para un colegio"""
    colegio = Colegio.query.get_or_404(id_colegio)
    precios = PrecioColegio.query.filter_by(id_colegio=id_colegio).all()

    productos_map = {}
    for precio in precios:
        pid = precio.id_producto
        if pid not in productos_map:
            productos_map[pid] = {
                'id_producto': pid,
                'nombre': precio.producto.nombre,
                'tipo': precio.producto.tipo,
                'tallas': []
            }

        stocks = Stock.query.filter_by(
            id_colegio=id_colegio,
            id_producto=pid
        ).filter(Stock.cantidad > 0).all()

        ahora = datetime.utcnow()
        for s in stocks:
            if not s.talla_individual:
                continue
            # Restar reservas activas no expiradas para mostrar stock real
            reservas_activas = db.session.query(
                func.coalesce(func.sum(Reserva.cantidad), 0)
            ).filter(
                Reserva.id_colegio == id_colegio,
                Reserva.id_producto == pid,
                Reserva.talla == s.talla_individual,
                Reserva.estado == 'activa',
                Reserva.fecha_expiracion > ahora,
            ).scalar() or 0

            stock_disponible = max(0, s.cantidad - reservas_activas)
            if stock_disponible > 0:
                productos_map[pid]['tallas'].append({
                    'talla': s.talla_individual,
                    'precio': precio.precio_unitario,
                    'stock': stock_disponible,
                    'talla_grupo': precio.talla_grupo,
                })

    catalogo = [p for p in productos_map.values() if p['tallas']]

    return jsonify({
        'colegio': {'id_colegio': colegio.id_colegio, 'nombre': colegio.nombre},
        'productos': catalogo
    }), 200


# ══════════════════════════════════════════════════════════════
# RESERVAR — reserva temporal de stock (15 minutos)
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/reservar', methods=['POST'])
def reservar_producto():
    """Reserva temporalmente un producto por 15 minutos para el carrito."""
    data = request.get_json() or {}

    session_id  = (data.get('session_id') or '').strip()
    id_colegio  = data.get('id_colegio')
    id_producto = data.get('id_producto')
    talla       = (data.get('talla') or '').strip()
    cantidad    = data.get('cantidad', 1)

    if not all([session_id, id_colegio, id_producto, talla]):
        return jsonify({'error': 'Datos incompletos'}), 400

    try:
        id_colegio  = int(id_colegio)
        id_producto = int(id_producto)
        cantidad    = int(cantidad)
        if cantidad < 1:
            return jsonify({'error': 'Cantidad inválida'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Datos inválidos'}), 400

    stock = Stock.query.filter_by(
        id_colegio=id_colegio,
        id_producto=id_producto,
        talla_individual=talla,
    ).first()

    if not stock or stock.cantidad == 0:
        return jsonify({'error': 'Sin stock para esta talla'}), 409

    ahora = datetime.utcnow()

    # Reservas activas de OTRAS sesiones
    reservas_otros = db.session.query(
        func.coalesce(func.sum(Reserva.cantidad), 0)
    ).filter(
        Reserva.id_colegio == id_colegio,
        Reserva.id_producto == id_producto,
        Reserva.talla == talla,
        Reserva.estado == 'activa',
        Reserva.fecha_expiracion > ahora,
        Reserva.session_id != session_id,
    ).scalar() or 0

    # Reserva activa de esta misma sesión (si ya había agregado antes)
    reserva_propia = Reserva.query.filter(
        Reserva.session_id == session_id,
        Reserva.id_colegio == id_colegio,
        Reserva.id_producto == id_producto,
        Reserva.talla == talla,
        Reserva.estado == 'activa',
        Reserva.fecha_expiracion > ahora,
    ).first()

    cantidad_propia = reserva_propia.cantidad if reserva_propia else 0
    stock_disponible = max(0, stock.cantidad - reservas_otros - cantidad_propia)

    if stock_disponible < cantidad:
        disp = stock_disponible + cantidad_propia  # cuánto puede pedir en total esta sesión
        if disp <= 0:
            return jsonify({'error': 'Sin stock disponible para esta talla'}), 409
        return jsonify({'error': f'Solo quedan {stock_disponible} unidades disponibles'}), 409

    nueva_expiracion = ahora + timedelta(minutes=15)

    if reserva_propia:
        # Sumar cantidad y renovar expiración
        reserva_propia.cantidad += cantidad
        reserva_propia.fecha_expiracion = nueva_expiracion
        db.session.commit()
        return jsonify({'id_reserva': reserva_propia.id_reserva, 'ok': True}), 200
    else:
        nueva = Reserva(
            session_id=session_id,
            id_colegio=id_colegio,
            id_producto=id_producto,
            talla=talla,
            cantidad=cantidad,
            fecha_expiracion=nueva_expiracion,
        )
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'id_reserva': nueva.id_reserva, 'ok': True}), 201


# ══════════════════════════════════════════════════════════════
# CREAR PEDIDO — genera preferencia de MercadoPago
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/pedido', methods=['POST'])
def crear_pedido():
    """Crea un pedido web y retorna el link de pago de MercadoPago"""
    data = request.get_json()

    requeridos = ['nombre_cliente', 'email_cliente', 'telefono_cliente', 'id_colegio', 'items']
    for campo in requeridos:
        if not data.get(campo):
            return jsonify({'error': f'Campo requerido: {campo}'}), 400

    items = data['items']
    if not items or not isinstance(items, list):
        return jsonify({'error': 'El carrito está vacío'}), 400

    print(f"[PEDIDO] id_colegio={data['id_colegio']} items={[(i.get('id_producto'), i.get('talla'), i.get('nombre')) for i in items]}", flush=True)

    colegio = Colegio.query.get(data['id_colegio'])
    if not colegio:
        return jsonify({'error': 'Colegio no encontrado'}), 404

    # Validar stock y calcular total
    total = 0
    items_validados = []
    ahora = datetime.utcnow()
    for item in items:
        id_reserva = item.get('id_reserva')

        if id_reserva:
            # Validar que la reserva siga activa
            reserva = Reserva.query.get(id_reserva)
            if not reserva or reserva.estado != 'activa' or reserva.fecha_expiracion < ahora:
                return jsonify({
                    'error': f"La reserva de {item.get('nombre', '')} talla {item.get('talla', '')} "
                             f"expiró. Vuelve a agregar el producto al carrito."
                }), 409
            if reserva.cantidad < item['cantidad']:
                return jsonify({
                    'error': f"La cantidad reservada de {item.get('nombre', '')} es insuficiente."
                }), 409
        else:
            # Sin reserva: validar stock directo (compatibilidad hacia atrás)
            stock = Stock.query.filter_by(
                id_colegio=data['id_colegio'],
                id_producto=item['id_producto'],
                talla_individual=item['talla']
            ).first()
            print(f"[STOCK] buscando id_colegio={data['id_colegio']} id_producto={item['id_producto']} talla={repr(item['talla'])} → encontrado={stock is not None} cantidad={stock.cantidad if stock else 'N/A'}", flush=True)
            if not stock or stock.cantidad < item['cantidad']:
                return jsonify({'error': f"Sin stock: {item.get('nombre', '')} talla {item.get('talla', '')}"}), 400

        precio = PrecioColegio.query.filter_by(
            id_colegio=data['id_colegio'],
            id_producto=item['id_producto'],
        ).first()

        if not precio:
            return jsonify({'error': f"Precio no encontrado: {item.get('nombre', '')}"}), 400

        subtotal_item = precio.precio_unitario * item['cantidad']
        total += subtotal_item
        items_validados.append({
            'id_producto':  item['id_producto'],
            'nombre':       item.get('nombre', ''),
            'talla':        item['talla'],
            'cantidad':     item['cantidad'],
            'precio_unitario': precio.precio_unitario,
            'subtotal':     subtotal_item,
            'id_reserva':   id_reserva,
        })

    referencia = f"RALOZ-{uuid.uuid4().hex[:12].upper()}"

    # Crear pedido en DB
    pedido = PedidoWeb(
        referencia=referencia,
        nombre_cliente=data['nombre_cliente'],
        email_cliente=data['email_cliente'],
        telefono_cliente=data['telefono_cliente'],
        documento_cliente=data.get('documento_cliente', ''),
        id_colegio=colegio.id_colegio,
        nombre_colegio=colegio.nombre,
        items_json=json.dumps(items_validados),
        total=total,
        estado='pendiente',
    )
    db.session.add(pedido)
    db.session.commit()

    # Crear preferencia en MercadoPago
    mp_token = os.getenv('MP_ACCESS_TOKEN', '')
    redirect_base = os.getenv('MP_REDIRECT_URL', 'https://ralozcol-web.pages.dev')
    backend_url   = os.getenv('BACKEND_URL', 'https://raloz-web.onrender.com')

    logger.info('[MP] token presente: %s | redirect_base: %s', bool(mp_token), redirect_base)

    pago_url = None
    if mp_token:
        try:
            nombre_partes = data['nombre_cliente'].split(' ', 1)
            preference_data = {
                'external_reference': referencia,
                'items': [
                    {
                        'id': str(i['id_producto']),
                        'title': f"{i['nombre']} — Talla {i['talla']}",
                        'quantity': i['cantidad'],
                        'unit_price': float(i['precio_unitario']),
                        'currency_id': 'COP',
                    }
                    for i in items_validados
                ],
                'payer': {
                    'name': nombre_partes[0],
                    'surname': nombre_partes[1] if len(nombre_partes) > 1 else '',
                    'email': data['email_cliente'],
                    'phone': {'number': data['telefono_cliente']},
                },
                'back_urls': {
                    'success': f"{redirect_base}?estado=aprobado&ref={referencia}",
                    'failure': f"{redirect_base}?estado=fallido&ref={referencia}",
                    'pending': f"{redirect_base}?estado=pendiente&ref={referencia}",
                },
                'auto_return': 'approved',
                'notification_url': f"{backend_url}/api/tienda/mp/webhook",
                'statement_descriptor': 'RALOZ UNIFORMES',
            }

            resp = requests.post(
                f'{MP_API}/checkout/preferences',
                json=preference_data,
                headers={
                    'Authorization': f'Bearer {mp_token}',
                    'Content-Type': 'application/json',
                },
                timeout=20,
            )

            if resp.status_code in (200, 201):
                mp_data = resp.json()
                pago_url = mp_data.get('init_point')
                pedido.wompi_transaction_id = mp_data.get('id')
                db.session.commit()
            else:
                logger.error('[MP] Preferencia rechazada %s: %s', resp.status_code, resp.text)

        except Exception as e:
            logger.error('[MP] Error creando preferencia: %s', str(e))

    return jsonify({
        'pedido': {
            'referencia': referencia,
            'id_pedido': pedido.id_pedido,
            'total': total,
            'items': items_validados,
        },
        'pago_url': pago_url,
    }), 201


# ══════════════════════════════════════════════════════════════
# WEBHOOK MERCADOPAGO — confirmación de pago
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/mp/webhook', methods=['POST'])
def mp_webhook():
    """Recibe notificaciones de MercadoPago y procesa pagos aprobados"""
    data = request.get_json() or {}
    topic = data.get('type') or request.args.get('topic', '')
    resource_id = data.get('data', {}).get('id') or request.args.get('id', '')

    if topic not in ('payment', 'merchant_order'):
        return jsonify({'ok': True}), 200

    mp_token = os.getenv('MP_ACCESS_TOKEN', '')
    if not mp_token or not resource_id:
        return jsonify({'ok': True}), 200

    try:
        # Obtener detalle del pago desde MP
        url = f'{MP_API}/v1/payments/{resource_id}' if topic == 'payment' else f'{MP_API}/merchant_orders/{resource_id}'
        resp = requests.get(url, headers={'Authorization': f'Bearer {mp_token}'}, timeout=8)
        if resp.status_code != 200:
            return jsonify({'ok': True}), 200

        pago_data = resp.json()
        estado_mp = pago_data.get('status', '')
        referencia = pago_data.get('external_reference', '')
        metodo = pago_data.get('payment_type_id', 'MP')

        if not referencia:
            return jsonify({'ok': True}), 200

        pedido = PedidoWeb.query.filter_by(referencia=referencia).first()
        if not pedido:
            return jsonify({'ok': True}), 200

        pedido.wompi_status = estado_mp
        pedido.metodo_pago = metodo

        if estado_mp == 'approved' and pedido.estado == 'pendiente':
            pedido.estado = 'pagado'
            pedido.fecha_pago = datetime.utcnow()
            factura = None
            try:
                factura = _crear_factura_desde_pedido(pedido)
                pedido.id_factura = factura.id_factura
            except Exception:
                db.session.rollback()

            # Enviar email con factura PDF al cliente (fallo no bloquea la respuesta)
            if factura and pedido.email_cliente:
                try:
                    detalles = list(factura.detalles)
                    enviar_email_factura(pedido.email_cliente, factura, detalles)
                except Exception as e:
                    logger.error('[WEBHOOK] Error enviando email: %s', str(e))

        elif estado_mp in ('rejected', 'cancelled', 'refunded', 'charged_back'):
            pedido.estado = 'fallido'
            # Liberar reservas para que el stock vuelva a estar disponible
            try:
                items_pedido = json.loads(pedido.items_json) if pedido.items_json else []
                for item in items_pedido:
                    if item.get('id_reserva'):
                        reserva = Reserva.query.get(item['id_reserva'])
                        if reserva and reserva.estado == 'activa':
                            reserva.estado = 'cancelada'
            except Exception:
                pass

        db.session.commit()

    except Exception:
        pass

    return jsonify({'ok': True}), 200


# ══════════════════════════════════════════════════════════════
# ADMIN — Gestión de pedidos online (requiere JWT)
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/admin/pedidos', methods=['GET'])
def listar_pedidos_admin():
    """Lista todos los pedidos online con filtros. Requiere JWT."""
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception:
        return jsonify({'error': 'No autorizado'}), 401

    estado  = request.args.get('estado', '').strip()
    limit   = min(request.args.get('limit', 50, type=int), 200)
    offset  = request.args.get('offset', 0, type=int)

    query = PedidoWeb.query
    if estado:
        query = query.filter(PedidoWeb.estado == estado)
    query = query.order_by(PedidoWeb.fecha_creacion.desc())

    total  = query.count()
    pedidos = query.offset(offset).limit(limit).all()

    return jsonify({
        'pedidos': [p.to_dict() for p in pedidos],
        'total':   total,
        'limit':   limit,
        'offset':  offset,
    }), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>', methods=['GET'])
def detalle_pedido_admin(id_pedido):
    """Detalle de un pedido con sus items. Requiere JWT."""
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception:
        return jsonify({'error': 'No autorizado'}), 401

    pedido = PedidoWeb.query.get_or_404(id_pedido)
    d = pedido.to_dict()

    if pedido.id_factura:
        factura = Factura.query.get(pedido.id_factura)
        if factura:
            d['factura_numero'] = factura.numero_factura
            d['factura_id']     = factura.id_factura

    return jsonify({'pedido': d}), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/factura.pdf', methods=['GET'])
def descargar_factura_admin(id_pedido):
    """Genera y descarga el PDF de la factura de un pedido. Requiere JWT."""
    from flask_jwt_extended import verify_jwt_in_request
    from flask import Response
    from app.utils.email_service import generar_pdf_factura
    try:
        verify_jwt_in_request()
    except Exception:
        return jsonify({'error': 'No autorizado'}), 401

    pedido = PedidoWeb.query.get_or_404(id_pedido)
    if not pedido.id_factura:
        return jsonify({'error': 'Este pedido no tiene factura aún'}), 404

    factura  = Factura.query.get_or_404(pedido.id_factura)
    detalles = list(factura.detalles)
    pdf_buf  = generar_pdf_factura(factura, detalles)

    return Response(
        pdf_buf.read(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="Factura-{factura.numero_factura}.pdf"',
        },
    )


# ══════════════════════════════════════════════════════════════
# CONSULTAR ESTADO DEL PEDIDO
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/pedido/<referencia>', methods=['GET'])
def consultar_pedido(referencia):
    pedido = PedidoWeb.query.filter_by(referencia=referencia).first()
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    return jsonify({'pedido': pedido.to_dict()}), 200


# ══════════════════════════════════════════════════════════════
# HELPERS PRIVADOS
# ══════════════════════════════════════════════════════════════

def _crear_factura_desde_pedido(pedido: PedidoWeb) -> Factura:
    """Convierte un PedidoWeb pagado en una Factura del sistema"""
    items = json.loads(pedido.items_json)

    serie = SerieFacturacion.query.filter_by(activa=True).first()
    if not serie:
        raise ValueError('No hay serie de facturación activa')
    serie.consecutivo_actual += 1
    numero = serie.formato.format(ano=serie.ano, consecutivo=serie.consecutivo_actual)

    cliente = Cliente.query.filter_by(email=pedido.email_cliente).first()
    if not cliente:
        cliente = Cliente(
            nombre=pedido.nombre_cliente,
            telefono=pedido.telefono_cliente,
            email=pedido.email_cliente,
            documento=pedido.documento_cliente or '',
        )
        db.session.add(cliente)
        db.session.flush()

    factura = Factura(
        numero_factura=numero,
        id_colegio=pedido.id_colegio,
        cliente_nombre=pedido.nombre_cliente,
        cliente_telefono=pedido.telefono_cliente,
        cliente_email=pedido.email_cliente,
        cliente_nit=pedido.documento_cliente or '',
        fecha_factura=date.today(),
        total=pedido.total,
        subtotal=pedido.total,
        total_abonado=pedido.total,
        saldo_pendiente=0,
        estado='PAGADA',
        estado_entrega='POR_ENTREGAR',
        metodo_pago=pedido.metodo_pago or 'MP',
        observaciones=f'Pedido web #{pedido.referencia}',
        usuario_creacion='TIENDA_WEB',
    )
    db.session.add(factura)
    db.session.flush()

    for item in items:
        db.session.add(FacturaDetalle(
            id_factura=factura.id_factura,
            id_producto=item['id_producto'],
            talla_individual=item['talla'],
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario'],
            total_linea=item['subtotal'],
        ))
        stock = Stock.query.filter_by(
            id_colegio=pedido.id_colegio,
            id_producto=item['id_producto'],
            talla_individual=item['talla'],
        ).first()
        if stock:
            stock.cantidad = max(0, stock.cantidad - item['cantidad'])

        # Marcar reserva como completada
        if item.get('id_reserva'):
            reserva = Reserva.query.get(item['id_reserva'])
            if reserva:
                reserva.estado = 'completada'

    metodo_pago = MetodoPago.query.filter_by(nombre='TRANSFERENCIA').first()
    db.session.add(Pago(
        id_factura=factura.id_factura,
        monto=pedido.total,
        id_metodo_pago=metodo_pago.id_metodo_pago if metodo_pago else 1,
        observacion=f'Pago online MercadoPago — {pedido.referencia}',
        fecha_pago=date.today(),
    ))
    db.session.commit()

    return factura
