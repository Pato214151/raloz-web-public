"""
API Pública de Tienda Online — RALOZ COL SAS
Endpoints sin autenticación para la página web de Netlify
Pagos procesados por MercadoPago (persona natural)
"""

import os
import json
import time
import uuid
import hmac
import hashlib
import logging
import threading
import requests
from datetime import datetime, date, timedelta
from sqlalchemy import func
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)
from app import db, limiter
from app.utils.email_service import enviar_email_factura
from app.utils.tallas import TALLA_GRUPO_A_INDIVIDUALES, TALLA_INDIVIDUAL_A_GRUPO
from app.utils.whatsapp_notify import notificar_whatsapp
from app.utils.validators import sanitize_string, validate_email
from app.utils.decorators import registrar_auditoria
from app.models import (
    Colegio, Producto, PrecioColegio, Stock,
    PedidoWeb, Factura, FacturaDetalle, Pago,
    SerieFacturacion, Cliente, Reserva,
    PedidoFabricacion, StockPendienteFabricacion,
)

# Orden canónico de tallas individuales para mostrar en la tienda
_ORDEN_TALLAS = ['4', '6', '8', '10', '12', '14', '16', 'S', 'M', 'L', 'XL']

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
    """Retorna TODOS los productos con precios para un colegio, con stock real por talla."""
    colegio = Colegio.query.get_or_404(id_colegio)
    precios = PrecioColegio.query.filter_by(id_colegio=id_colegio).all()

    # 1er paso: construir meta de productos y tabla de precios por talla
    productos_meta = {}   # pid → {nombre, tipo}
    precios_por_pid = {}  # pid → {talla_grupo: precio_unitario}
    for precio in precios:
        pid = precio.id_producto
        if pid not in productos_meta:
            productos_meta[pid] = {
                'nombre': precio.producto.nombre,
                'tipo':   precio.producto.tipo,
            }
        precios_por_pid.setdefault(pid, {})[precio.talla_grupo] = precio.precio_unitario

    # 2do paso: expandir talla_grupo → tallas individuales con su precio
    # (6-8 → 6 y 8 con el mismo precio, 10-12 → 10 y 12, etc.)
    catalogo = []
    ahora = datetime.utcnow()
    for pid, meta in productos_meta.items():
        tallas_precios = precios_por_pid.get(pid, {})

        # Construir mapa talla_individual → precio desde los grupos configurados
        talla_precio_map = {}
        for talla_grupo, precio_u in tallas_precios.items():
            if not precio_u or precio_u <= 0:
                continue
            for talla_ind in TALLA_GRUPO_A_INDIVIDUALES.get(talla_grupo, [talla_grupo]):
                talla_precio_map[talla_ind] = precio_u

        if not talla_precio_map:
            continue

        # Batch: stock de todas las tallas individuales en una sola query
        stocks_rows = Stock.query.filter_by(
            id_colegio=id_colegio,
            id_producto=pid,
        ).filter(Stock.talla_individual.in_(list(talla_precio_map.keys()))).all()
        stock_map = {s.talla_individual: s.cantidad for s in stocks_rows}

        # Batch: reservas activas agrupadas por talla (solo tallas con stock > 0)
        tallas_con_stock = [t for t, s in stock_map.items() if s > 0]
        reservas_map = {}
        if tallas_con_stock:
            reservas_rows = db.session.query(
                Reserva.talla,
                func.coalesce(func.sum(Reserva.cantidad), 0).label('total'),
            ).filter(
                Reserva.id_colegio == id_colegio,
                Reserva.id_producto == pid,
                Reserva.talla.in_(tallas_con_stock),
                Reserva.estado == 'activa',
                Reserva.fecha_expiracion > ahora,
            ).group_by(Reserva.talla).all()
            reservas_map = {r.talla: int(r.total) for r in reservas_rows}

        # Construir lista de tallas en orden canónico (4,6,8,10,12,14,16,S,M,L,XL)
        tallas = []
        for talla_ind in sorted(
            talla_precio_map.keys(),
            key=lambda t: _ORDEN_TALLAS.index(t) if t in _ORDEN_TALLAS else 99,
        ):
            stock_bruto = stock_map.get(talla_ind, 0)
            reservas = reservas_map.get(talla_ind, 0)
            tallas.append({
                'talla':  talla_ind,
                'precio': talla_precio_map[talla_ind],
                'stock':  max(0, stock_bruto - reservas),
            })

        todas_sin_stock = all(t['stock'] == 0 for t in tallas)
        catalogo.append({
            'id_producto': pid,
            'nombre':      meta['nombre'],
            'tipo':        meta['tipo'],
            'tallas':      tallas,
            'fabricacion': todas_sin_stock,
        })

    return jsonify({
        'colegio': {'id_colegio': colegio.id_colegio, 'nombre': colegio.nombre},
        'productos': catalogo
    }), 200


# ══════════════════════════════════════════════════════════════
# RESERVAR — reserva temporal de stock
# MEJORA #6: Cambiado de 15 → 30 minutos para dar más tiempo
# al cliente en el checkout (especialmente en móvil).
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/reservar', methods=['POST'])
@limiter.limit("20 per minute")  # evita que se agote el stock con reservas masivas
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

    nueva_expiracion = ahora + timedelta(minutes=30)

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
# LIBERAR RESERVAS — devuelve stock cuando el cliente quita
# items del carrito (antes quedaba secuestrado hasta 30 min).
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/reservar/liberar', methods=['POST'])
@limiter.limit("30 per minute")
def liberar_reservas():
    """
    Cancela reservas activas de una sesión del carrito.
    El session_id (UUID secreto del navegador) actúa como credencial:
    solo permite liberar las reservas de esa misma sesión.
    Si se envía ids_reserva, libera solo esas; si no, todas las de la sesión.
    """
    data = request.get_json() or {}
    session_id = (data.get('session_id') or '').strip()
    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    query = Reserva.query.filter(
        Reserva.session_id == session_id,
        Reserva.estado == 'activa',
    )

    ids_reserva = data.get('ids_reserva')
    if ids_reserva:
        try:
            ids_reserva = [int(x) for x in ids_reserva]
        except (ValueError, TypeError):
            return jsonify({'error': 'ids_reserva inválidos'}), 400
        query = query.filter(Reserva.id_reserva.in_(ids_reserva))

    liberadas = 0
    for reserva in query.all():
        reserva.estado = 'cancelada'
        liberadas += 1
    db.session.commit()

    if liberadas:
        logger.info('[RESERVA] %d reserva(s) liberadas para sesión %s…', liberadas, session_id[:8])
    return jsonify({'ok': True, 'liberadas': liberadas}), 200


# ══════════════════════════════════════════════════════════════
# CREAR PEDIDO — genera preferencia de MercadoPago
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/pedido', methods=['POST'])
@limiter.limit("10 per minute")  # evita creación masiva de pedidos falsos
def crear_pedido():
    """Crea un pedido web y retorna el link de pago de MercadoPago"""
    data = request.get_json()

    requeridos = ['nombre_cliente', 'email_cliente', 'telefono_cliente', 'items']
    for campo in requeridos:
        if not data.get(campo):
            return jsonify({'error': f'Campo requerido: {campo}'}), 400

    # Sanitizar datos del cliente (van al PDF y a WhatsApp) — anti-inyección
    data['nombre_cliente']    = sanitize_string(data.get('nombre_cliente'), 200)
    data['documento_cliente'] = sanitize_string(data.get('documento_cliente'), 50)
    data['direccion_envio']   = sanitize_string(data.get('direccion_envio'), 300)
    data['telefono_cliente']  = sanitize_string(data.get('telefono_cliente'), 50)
    data['email_cliente']     = sanitize_string(data.get('email_cliente'), 200)
    if not validate_email(data['email_cliente']):
        return jsonify({'error': 'Correo electrónico inválido'}), 400

    items = data['items']
    if not items or not isinstance(items, list):
        return jsonify({'error': 'El carrito está vacío'}), 400

    # Porcentaje de abono (50 o 100). Solo aplica si hay items de fabricación.
    abono_porcentaje = int(data.get('abono_porcentaje', 100))
    if abono_porcentaje not in (50, 100):
        abono_porcentaje = 100

    # tipo_entrega: 'parcial' (recibir disponible ahora) o 'completa' (esperar todo)
    tipo_entrega = data.get('tipo_entrega', 'completa')
    if tipo_entrega not in ('parcial', 'completa'):
        tipo_entrega = 'completa'

    # id_colegio es opcional: null para pedidos de relojes u otras categorías generales
    id_colegio_raw = data.get('id_colegio')
    colegio = None
    nombre_colegio_str = 'Tienda General'
    if id_colegio_raw:
        colegio = Colegio.query.get(id_colegio_raw)
        if not colegio:
            return jsonify({'error': 'Colegio no encontrado'}), 404
        nombre_colegio_str = colegio.nombre

    logger.info(
        '[PEDIDO] id_colegio=%s colegio=%s abono=%s%% entrega=%s items=%s',
        id_colegio_raw, nombre_colegio_str, abono_porcentaje, tipo_entrega,
        [(i.get('id_producto'), i.get('talla'), i.get('tipo_pedido', 'normal')) for i in items],
    )

    total_orden = 0
    items_validados = []
    tiene_fabricacion = False
    ahora = datetime.utcnow()

    for item in items:
        id_reserva = item.get('id_reserva')
        categoria  = item.get('categoria', '')
        cantidad   = int(item.get('cantidad', 1))

        # ── Productos sin colegio (relojes, etc.) ──────────────────────────
        # El precio viene del frontend porque no hay PrecioColegio para ellos.
        if not id_colegio_raw or categoria == 'relojes':
            precio_unitario = float(item.get('unit_price') or item.get('precio', 0))
            if not precio_unitario:
                return jsonify({'error': f"Precio inválido: {item.get('nombre', '')}"}), 400
            subtotal_item = precio_unitario * cantidad
            total_orden  += subtotal_item
            items_validados.append({
                'id_producto':     item['id_producto'],
                'nombre':          item.get('nombre', ''),
                'talla':           item.get('talla', ''),
                'cantidad':        cantidad,
                'precio_unitario': precio_unitario,
                'subtotal':        subtotal_item,
                'id_reserva':      None,
                'tipo_pedido':     'general',
                'stock_disponible': cantidad,
                'categoria':       categoria,
            })
            continue

        # ── Clasificación server-side (backend decide el tipo, no el frontend) ──
        tipo_pedido, stock_disponible = _clasificar_item(
            id_colegio_raw, item['id_producto'], item.get('talla', ''),
            cantidad, id_reserva, ahora,
        )
        if tipo_pedido in ('fabricacion', 'mixto'):
            tiene_fabricacion = True

        logger.info(
            '[PEDIDO] producto=%s talla=%s tipo=%s stock_disp=%s',
            item['id_producto'], item.get('talla'), tipo_pedido, stock_disponible,
        )

        # ── Precio autoritativo desde PrecioColegio (backend) ──────────────
        talla_grupo = TALLA_INDIVIDUAL_A_GRUPO.get(item.get('talla', ''), item.get('talla', ''))
        precio = (
            PrecioColegio.query.filter_by(
                id_colegio=id_colegio_raw,
                id_producto=item['id_producto'],
                talla_grupo=talla_grupo,
            ).first()
            or PrecioColegio.query.filter_by(
                id_colegio=id_colegio_raw,
                id_producto=item['id_producto'],
            ).first()
        )
        if not precio:
            return jsonify({'error': f"Precio no encontrado: {item.get('nombre', '')}"}), 400

        precio_unitario = precio.precio_unitario
        subtotal_item   = precio_unitario * cantidad
        total_orden    += subtotal_item
        items_validados.append({
            'id_producto':      item['id_producto'],
            'nombre':           item.get('nombre', ''),
            'talla':            item.get('talla', ''),
            'cantidad':         cantidad,
            'precio_unitario':  precio_unitario,
            'subtotal':         subtotal_item,
            'id_reserva':       id_reserva,
            'tipo_pedido':      tipo_pedido,
            'stock_disponible': stock_disponible,
        })

    # Monto a cobrar ahora (puede ser 50% si es pedido con abono)
    if tiene_fabricacion and abono_porcentaje == 50:
        total_cobrar = round(total_orden * 0.5)
    else:
        total_cobrar    = total_orden
        abono_porcentaje = 100

    referencia = f"RALOZ-{uuid.uuid4().hex[:12].upper()}"

    pedido = PedidoWeb(
        referencia=referencia,
        nombre_cliente=data['nombre_cliente'],
        email_cliente=data['email_cliente'],
        telefono_cliente=data['telefono_cliente'],
        documento_cliente=data.get('documento_cliente', ''),
        direccion_envio=data.get('direccion_envio', '') or '',
        id_colegio=colegio.id_colegio if colegio else None,
        nombre_colegio=nombre_colegio_str,
        items_json=json.dumps(items_validados),
        total=total_cobrar,
        total_orden=total_orden,
        abono_porcentaje=abono_porcentaje,
        tiene_fabricacion=tiene_fabricacion,
        # MEJORA #5: respetar el tipo_entrega que envía el frontend
        tipo_entrega=tipo_entrega,
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
            # Cuando es abono del 50%, enviamos un item único con el monto correcto.
            # Si enviamos los items completos, MP cobraría el total_orden, no el 50%.
            if tiene_fabricacion and abono_porcentaje == 50:
                mp_items = [{
                    'id': 'ABONO_50',
                    'title': f'Abono 50% — Pedido {referencia}',
                    'quantity': 1,
                    'unit_price': float(total_cobrar),
                    'currency_id': 'COP',
                }]
            else:
                mp_items = [
                    {
                        'id': str(i['id_producto']),
                        'title': f"{i['nombre']} — Talla {i['talla']}",
                        'quantity': i['cantidad'],
                        'unit_price': float(i['precio_unitario']),
                        'currency_id': 'COP',
                    }
                    for i in items_validados
                ]

            preference_data = {
                'external_reference': referencia,
                'items': mp_items,
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
                # MEJORA #7: usar mp_preference_id en vez de wompi_transaction_id
                pedido.mp_preference_id = mp_data.get('id')
                db.session.commit()
            else:
                logger.error('[MP] Preferencia rechazada %s: %s', resp.status_code, resp.text)

        except Exception as e:
            logger.error('[MP] Error creando preferencia: %s', str(e))

    return jsonify({
        'pedido': {
            'referencia':        referencia,
            'id_pedido':         pedido.id_pedido,
            'total_cobrar':      total_cobrar,
            'total_orden':       total_orden,
            'abono_porcentaje':  abono_porcentaje,
            'tiene_fabricacion': tiene_fabricacion,
            'items':             items_validados,
        },
        'pago_url': pago_url,
    }), 201


# ══════════════════════════════════════════════════════════════
# PAGAR SALDO — genera link de MP para saldo pendiente
# ══════════════════════════════════════════════════════════════

def _generar_link_saldo(pedido, factura):
    """Crea una preferencia de MercadoPago para el saldo pendiente.
    Devuelve el init_point (URL de pago) o None si falla."""
    mp_token = os.getenv('MP_ACCESS_TOKEN', '')
    if not mp_token:
        logger.error('[PAGAR-SALDO] MP_ACCESS_TOKEN no configurado')
        return None

    backend_url   = os.getenv('BACKEND_URL', 'https://raloz-web.onrender.com')
    redirect_base = os.getenv('MP_REDIRECT_URL', 'https://ralozcol-web.pages.dev')
    saldo_ref     = f"{pedido.referencia}-SALDO"

    preference_data = {
        'external_reference': saldo_ref,
        'items': [{
            'id': 'SALDO',
            'title': f'Saldo pendiente — Pedido {pedido.referencia}',
            'quantity': 1,
            'unit_price': float(factura.saldo_pendiente),
            'currency_id': 'COP',
        }],
        'payer': {
            'name': (factura.cliente_nombre or pedido.nombre_cliente or '').split(' ')[0],
            'email': factura.cliente_email or pedido.email_cliente or '',
        },
        'back_urls': {
            'success': f"{redirect_base}?estado=saldo_pagado&ref={pedido.referencia}",
            'failure': f"{redirect_base}?estado=fallido&ref={pedido.referencia}",
            'pending': f"{redirect_base}?estado=pendiente&ref={pedido.referencia}",
        },
        'auto_return': 'approved',
        'notification_url': f"{backend_url}/api/tienda/mp/webhook",
        'statement_descriptor': 'RALOZ UNIFORMES',
    }

    try:
        resp = requests.post(
            f'{MP_API}/checkout/preferences',
            json=preference_data,
            headers={'Authorization': f'Bearer {mp_token}', 'Content-Type': 'application/json'},
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            logger.error('[PAGAR-SALDO] MP error %s: %s', resp.status_code, resp.text[:300])
            return None
        return resp.json().get('init_point')
    except Exception as e:
        logger.error('[PAGAR-SALDO] Error generando link: %s', str(e), exc_info=True)
        return None


@tienda_bp.route('/pagar-saldo', methods=['POST'])
@limiter.limit("10 per minute")
def pagar_saldo():
    """
    Genera un link de MercadoPago para pagar el saldo pendiente.
    Lo puede llamar el admin (al marcar listo), el bot de WhatsApp, o el cliente.
    Solo genera link si el pedido ya está LISTO PARA ENTREGA y tiene saldo > 0.
    """
    data = request.get_json() or {}
    referencia = (data.get('referencia') or '').strip()
    if not referencia:
        return jsonify({'error': 'referencia requerida'}), 400

    pedido = PedidoWeb.query.filter_by(referencia=referencia).first()
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado', 'code': 'no_encontrado'}), 404
    if not pedido.id_factura:
        return jsonify({'error': 'El pedido aún no tiene factura', 'code': 'sin_factura'}), 400

    factura = Factura.query.get(pedido.id_factura)
    if not factura:
        return jsonify({'error': 'Factura no encontrada', 'code': 'no_encontrado'}), 404
    if not factura.saldo_pendiente or factura.saldo_pendiente <= 0:
        return jsonify({'error': 'Este pedido ya está pagado en su totalidad', 'code': 'sin_saldo'}), 400

    # Solo permitir pagar el saldo cuando el pedido ya está listo (no en producción)
    pf = PedidoFabricacion.query.filter_by(id_pedido_web=pedido.id_pedido).first()
    if pf and pf.estado not in ('listo_para_entrega', 'entregado'):
        return jsonify({'error': 'El pedido aún se está fabricando', 'code': 'en_produccion'}), 400

    init_point = _generar_link_saldo(pedido, factura)
    if not init_point:
        return jsonify({'error': 'No se pudo generar el link de pago'}), 502

    logger.info('[PAGAR-SALDO] Link generado para %s: $%s', referencia, factura.saldo_pendiente)
    return jsonify({
        'pago_url':   init_point,
        'monto':      factura.saldo_pendiente,
        'referencia': referencia,
    }), 200


# ══════════════════════════════════════════════════════════════
# WEBHOOK MERCADOPAGO — confirmación de pago
# ══════════════════════════════════════════════════════════════

def _validar_firma_mp(data_id: str) -> bool:
    """
    MEJORA #2: Validar firma X-Signature de MercadoPago.
    MP envía: X-Signature: ts=<timestamp>,v1=<hmac_sha256>
    donde el mensaje firmado es: "ts=<ts>|data.id=<data_id>"
    Si MP_WEBHOOK_SECRET no está configurado, se omite la validación
    (backward compatible).
    """
    secreto = os.getenv('MP_WEBHOOK_SECRET', '')
    if not secreto:
        logger.warning('[WEBHOOK] MP_WEBHOOK_SECRET no configurado — saltando validación de firma')
        return True

    x_sig = request.headers.get('X-Signature', '')
    if not x_sig:
        logger.warning('[WEBHOOK] X-Signature ausente — rechazando')
        return False

    partes = {}
    for par in x_sig.split(','):
        if '=' in par:
            k, v = par.split('=', 1)
            partes[k.strip()] = v.strip()

    ts  = partes.get('ts', '')
    v1  = partes.get('v1', '')
    if not ts or not v1:
        logger.warning('[WEBHOOK] X-Signature mal formada: %s', x_sig)
        return False

    mensaje = f"ts={ts}|data.id={data_id}"
    esperado = hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(esperado, v1):
        logger.warning('[WEBHOOK] Firma inválida: esperada=%s recibida=%s', esperado, v1)
        return False

    return True


def _avisar_admin(texto):
    """Alerta al admin por WhatsApp (si ADMIN_WHATSAPP está configurado en el backend)."""
    admin = os.getenv('ADMIN_WHATSAPP', '').strip()
    if admin:
        try:
            notificar_whatsapp(admin, 'aviso_admin', {'texto': texto})
        except Exception:
            pass


def _procesar_pago_saldo(referencia_saldo, estado_mp, pago_data):
    """
    Procesa el pago del SALDO restante (referencia *-SALDO).
    Seguro: idempotente (no descuenta dos veces el mismo pago) y maneja el caso
    de que el saldo ya estuviera en 0 (pagado en el local) → avisa al admin.
    """
    referencia = referencia_saldo[:-6]  # quita "-SALDO"
    if estado_mp != 'approved':
        logger.info('[WEBHOOK-SALDO] %s estado=%s (no aprobado)', referencia, estado_mp)
        return jsonify({'ok': True}), 200

    pedido = PedidoWeb.query.filter_by(referencia=referencia).first()
    if not pedido or not pedido.id_factura:
        logger.warning('[WEBHOOK-SALDO] pedido/factura no encontrado: %s', referencia)
        return jsonify({'ok': True}), 200
    factura = Factura.query.get(pedido.id_factura)
    if not factura:
        return jsonify({'ok': True}), 200

    payment_id = str(pago_data.get('id') or '')

    # Idempotencia: este MISMO pago ya se procesó (MP reintenta el webhook)
    if payment_id and factura.mp_saldo_payment_id == payment_id:
        logger.info('[WEBHOOK-SALDO] pago %s ya procesado, ignorando reintento', payment_id)
        return jsonify({'ok': True}), 200

    saldo_actual = factura.saldo_pendiente or 0
    # El saldo ya estaba en 0 (pagó en el local o doble pago) → NO descontar, avisar
    if saldo_actual <= 0:
        monto = pago_data.get('transaction_amount')
        logger.error('[WEBHOOK-SALDO] %s: pago recibido pero el saldo ya era 0 (monto=%s). Posible doble pago — revisar/devolver.', referencia, monto)
        _avisar_admin(f'OJO: llegó pago de saldo del pedido {referencia} por ${monto}, '
                      f'pero el saldo ya estaba en $0. Posible doble pago — revisar y devolver.')
        return jsonify({'ok': True}), 200

    # Validar monto real pagado (no confiar en el link); para el saldo es el valor fijo
    monto = float(pago_data.get('transaction_amount') or saldo_actual)
    factura.total_abonado   = round((factura.total_abonado or 0) + monto, 2)
    factura.saldo_pendiente = round(max(0, saldo_actual - monto), 2)
    factura.mp_saldo_payment_id = payment_id
    if factura.saldo_pendiente <= 0:
        factura.estado = 'PAGADA'
    pf = PedidoFabricacion.query.filter_by(id_pedido_web=pedido.id_pedido).first()
    if pf:
        pf.saldo_pendiente = factura.saldo_pendiente
    db.session.commit()

    logger.info('[WEBHOOK-SALDO] %s saldo pagado (monto=%s, restante=%s)',
                referencia, monto, factura.saldo_pendiente)
    if pedido.telefono_cliente:
        notificar_whatsapp(pedido.telefono_cliente, 'saldo_pagado', {
            'nombre':     pedido.nombre_cliente,
            'referencia': referencia,
            'monto':      f"${int(monto):,}".replace(',', '.'),
        })
    return jsonify({'ok': True}), 200


@tienda_bp.route('/mp/webhook', methods=['POST'])
def mp_webhook():
    """Recibe notificaciones de MercadoPago y procesa pagos aprobados"""
    data = request.get_json() or {}
    topic = data.get('type') or request.args.get('topic', '')
    resource_id = data.get('data', {}).get('id') or request.args.get('id', '')

    if topic not in ('payment', 'merchant_order'):
        return jsonify({'ok': True}), 200

    # MEJORA #2: Validar firma antes de procesar
    if not _validar_firma_mp(resource_id or ''):
        return jsonify({'error': 'Firma inválida'}), 401

    mp_token = os.getenv('MP_ACCESS_TOKEN', '')
    if not mp_token or not resource_id:
        return jsonify({'ok': True}), 200

    # ── Consultar el detalle del pago en MP (con 1 reintento ante fallo transitorio) ──
    url = f'{MP_API}/v1/payments/{resource_id}' if topic == 'payment' else f'{MP_API}/merchant_orders/{resource_id}'
    pago_data = None
    for intento in range(2):
        try:
            resp = requests.get(url, headers={'Authorization': f'Bearer {mp_token}'}, timeout=8)
            if resp.status_code == 200:
                pago_data = resp.json()
                break
            logger.error('[WEBHOOK] MP status=%s: %s', resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning('[WEBHOOK] Fallo consulta MP (intento %d): %s', intento + 1, e)
        if intento == 0:
            time.sleep(1)

    if pago_data is None:
        # No pudimos confirmar el pago → devolver 500 para que MercadoPago REINTENTE el webhook
        # (así no se pierde el pago por un fallo transitorio de red/MP).
        logger.error('[WEBHOOK] No se pudo consultar MP (resource=%s); se pide reintento', resource_id)
        _avisar_admin(f'No pude confirmar un pago en MercadoPago (resource {resource_id}). '
                      f'MP reintentará automáticamente; si el aviso se repite, revisar.')
        return jsonify({'error': 'mp_unavailable'}), 500

    estado_mp  = pago_data.get('status', '')
    referencia = pago_data.get('external_reference', '')
    metodo     = pago_data.get('payment_type_id', 'MP')
    logger.info('[WEBHOOK] estado_mp=%s referencia=%s', estado_mp, referencia)

    if not referencia:
        return jsonify({'ok': True}), 200

    # ── Pago del SALDO restante (la referencia termina en -SALDO) ──
    if referencia.endswith('-SALDO'):
        return _procesar_pago_saldo(referencia, estado_mp, pago_data)

    pedido = PedidoWeb.query.filter_by(referencia=referencia).first()
    if not pedido:
        logger.warning('[WEBHOOK] Pedido no encontrado referencia=%s', referencia)
        return jsonify({'ok': True}), 200

    try:
        # Idempotencia REAL: si ya tiene factura, está todo hecho (no reprocesar)
        if estado_mp == 'approved' and pedido.id_factura:
            logger.info('[WEBHOOK] Pedido %s ya tiene factura, ignorando reintento', pedido.id_pedido)
            return jsonify({'ok': True}), 200

        pedido.wompi_status = estado_mp
        pedido.metodo_pago = metodo

        if estado_mp == 'approved':
            # Marcar pagado (pendiente, o 'pagado' sin factura = reintento que sana)
            if pedido.estado != 'pagado':
                pedido.estado = 'pagado'
                pedido.fecha_pago = datetime.utcnow()
                db.session.commit()

            # Crear factura — si falla, pedir reintento a MP para NO perder el pago
            try:
                factura = _crear_factura_desde_pedido(pedido)
                pedido.id_factura = factura.id_factura
                db.session.commit()
                logger.info('[WEBHOOK] Factura %s creada', factura.numero_factura)
            except Exception as e:
                db.session.rollback()
                logger.error('[WEBHOOK] Error creando factura %s: %s', referencia, e, exc_info=True)
                _avisar_admin(f'Pago aprobado de {referencia} pero FALLÓ crear la factura. '
                              f'MP reintentará; si persiste, crearla manual.')
                return jsonify({'error': 'factura_failed'}), 500

            # Email (hilo aparte, no bloquea)
            if pedido.email_cliente:
                _lanzar_email_async(pedido.email_cliente, factura.id_factura)

            # Aviso por WhatsApp: "tu orden se está preparando"
            if pedido.telefono_cliente:
                notificar_whatsapp(pedido.telefono_cliente, 'pago_confirmado', {
                    'nombre': pedido.nombre_cliente,
                    'referencia': pedido.referencia,
                    'total': f"${int(pedido.total):,}".replace(',', '.'),
                })

            try:
                _crear_pedido_fabricacion_si_aplica(pedido)
                db.session.commit()
            except Exception as e:
                logger.error('[WEBHOOK] Error fabricacion: %s', str(e), exc_info=True)
                db.session.rollback()

        elif estado_mp in ('refunded', 'charged_back') and pedido.id_factura:
            # Reembolso / contracargo de un pedido YA facturado (venta completada).
            # OJO: MercadoPago devolvió el DINERO, pero la prenda física no
            # necesariamente volvió al local. Por eso NO tocamos la factura ni el
            # stock automáticamente: avisamos al admin para que, cuando reciba la
            # prenda de vuelta, anule la factura en el panel (eso sí devuelve el
            # stock y actualiza la tienda). Marcamos 'reembolsado' para que el
            # reintento del webhook no mande el aviso dos veces.
            if pedido.estado != 'reembolsado':
                factura = Factura.query.get(pedido.id_factura)
                num = factura.numero_factura if factura else '?'
                logger.warning('[WEBHOOK] %s: %s de pedido YA facturado (factura=%s)',
                               referencia, estado_mp, num)
                accion = 'reembolsó' if estado_mp == 'refunded' else 'hizo contracargo (disputa) sobre'
                monto = f"${int(pedido.total):,}".replace(',', '.')
                _avisar_admin(
                    f'OJO: MercadoPago {accion} el pedido {referencia} '
                    f'(factura {num}, {monto}). El dinero ya se devolvió. '
                    f'Cuando el cliente devuelva la prenda, anula la factura en el '
                    f'panel para regresar el stock a la tienda.'
                )
                pedido.estado = 'reembolsado'
            db.session.commit()

        elif estado_mp in ('rejected', 'cancelled', 'refunded', 'charged_back'):
            # Pago que nunca llegó a completarse (rechazado/cancelado, o reembolso
            # de un pedido sin factura). Liberamos las reservas para devolver el
            # stock disponible de inmediato.
            logger.info('[WEBHOOK] Pedido %s → fallido (%s)', pedido.id_pedido, estado_mp)
            pedido.estado = 'fallido'
            try:
                items_pedido = json.loads(pedido.items_json) if pedido.items_json else []
                for item in items_pedido:
                    if item.get('id_reserva'):
                        reserva = Reserva.query.get(item['id_reserva'])
                        if reserva and reserva.estado == 'activa':
                            reserva.estado = 'cancelada'
            except Exception as e:
                logger.error('[WEBHOOK] Error liberando reservas: %s', str(e))
            db.session.commit()
        else:
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error('[WEBHOOK] Error general %s: %s', referencia, e, exc_info=True)
        _avisar_admin(f'Error procesando el pago del pedido {referencia}: {str(e)[:120]}. MP reintentará.')
        return jsonify({'error': 'processing_failed'}), 500

    return jsonify({'ok': True}), 200


# ══════════════════════════════════════════════════════════════
# ADMIN — Gestión de pedidos online (requiere JWT)
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/admin/pedidos', methods=['GET'])
@jwt_required()
def listar_pedidos_admin():
    """Lista todos los pedidos online con filtros. Requiere JWT."""
    estado  = request.args.get('estado', '').strip()
    limit   = min(request.args.get('limit', 50, type=int), 200)
    offset  = request.args.get('offset', 0, type=int)

    query = PedidoWeb.query
    if estado:
        query = query.filter(PedidoWeb.estado == estado)
    query = query.order_by(PedidoWeb.fecha_creacion.desc())

    total  = query.count()
    pedidos = query.offset(offset).limit(limit).all()

    # Enriquecer con estado_entrega de la factura asociada (bulk)
    factura_ids = [p.id_factura for p in pedidos if p.id_factura]
    facturas_map = {}
    if factura_ids:
        for f in Factura.query.filter(Factura.id_factura.in_(factura_ids)).all():
            facturas_map[f.id_factura] = f

    resultado = []
    for p in pedidos:
        d = p.to_dict()
        d['id_factura'] = p.id_factura
        if p.id_factura and p.id_factura in facturas_map:
            f = facturas_map[p.id_factura]
            d['estado_entrega'] = f.estado_entrega or 'POR_ENTREGAR'
            d['factura_numero'] = f.numero_factura
        else:
            d['estado_entrega'] = None
            d['factura_numero'] = None
        resultado.append(d)

    return jsonify({
        'pedidos': resultado,
        'total':   total,
        'limit':   limit,
        'offset':  offset,
    }), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>', methods=['GET'])
@jwt_required()
def detalle_pedido_admin(id_pedido):
    """Detalle de un pedido con sus items. Requiere JWT."""
    pedido = PedidoWeb.query.get_or_404(id_pedido)
    d = pedido.to_dict()

    d['id_factura'] = pedido.id_factura
    if pedido.id_factura:
        factura = Factura.query.get(pedido.id_factura)
        if factura:
            d['factura_numero']  = factura.numero_factura
            d['factura_id']      = factura.id_factura
            d['estado_entrega']  = factura.estado_entrega or 'POR_ENTREGAR'
    else:
        d['estado_entrega'] = None
        d['factura_numero'] = None

    return jsonify({'pedido': d}), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/marcar-pagado', methods=['POST'])
@jwt_required()
def marcar_pedido_pagado_manual(id_pedido):
    """Marca un pedido como pagado manualmente (cuando el webhook de MP falló). Requiere JWT."""
    pedido = PedidoWeb.query.get_or_404(id_pedido)

    if pedido.estado == 'pagado':
        return jsonify({'error': 'El pedido ya está marcado como pagado'}), 400

    pedido.estado = 'pagado'
    pedido.fecha_pago = datetime.utcnow()
    db.session.commit()

    factura = None
    error_factura = None
    try:
        factura = _crear_factura_desde_pedido(pedido)
        pedido.id_factura = factura.id_factura
        db.session.commit()
        logger.info('[MANUAL] Factura %s creada para pedido %s', factura.numero_factura, pedido.id_pedido)
    except Exception as e:
        error_factura = str(e)
        logger.error('[MANUAL] Error creando factura: %s', error_factura, exc_info=True)
        db.session.rollback()

    try:
        _crear_pedido_fabricacion_si_aplica(pedido)
    except Exception as e:
        logger.error('[MANUAL] Error fabricacion: %s', str(e))

    registrar_auditoria('pedidos_web', pedido.id_pedido, 'PAGO_MANUAL',
                        f'Pedido {pedido.referencia} marcado como pagado manualmente')
    return jsonify({
        'ok': True,
        'pedido': pedido.to_dict(),
        'factura_numero': factura.numero_factura if factura else None,
        'error_factura': error_factura,  # None si todo OK, mensaje si falló
    }), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/generar-factura', methods=['POST'])
@jwt_required()
def generar_factura_pedido(id_pedido):
    """Crea la factura para un pedido pagado que no la tiene aún (reintento tras error del webhook)."""
    pedido = PedidoWeb.query.get_or_404(id_pedido)
    if pedido.estado != 'pagado':
        return jsonify({'error': 'Solo se puede generar factura para pedidos pagados'}), 400
    if pedido.id_factura:
        return jsonify({'error': 'Este pedido ya tiene factura'}), 400

    try:
        factura = _crear_factura_desde_pedido(pedido)
        pedido.id_factura = factura.id_factura
        db.session.commit()
        logger.info('[FACTURA-MANUAL] Factura %s creada para pedido %s', factura.numero_factura, pedido.id_pedido)
    except Exception as e:
        db.session.rollback()
        logger.error('[FACTURA-MANUAL] Error: %s', str(e), exc_info=True)
        return jsonify({'error': 'No se pudo generar la factura'}), 500

    if pedido.email_cliente:
        try:
            enviar_email_factura(pedido.email_cliente, factura, list(factura.detalles))
        except Exception as e:
            logger.error('[FACTURA-MANUAL] Error email: %s', str(e))

    return jsonify({
        'ok': True,
        'factura_numero': factura.numero_factura,
        'pedido': pedido.to_dict(),
    }), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/reenviar-email', methods=['POST'])
@jwt_required()
def reenviar_email_pedido(id_pedido):
    """Reenvía el email de confirmación con la factura PDF al cliente."""
    pedido = PedidoWeb.query.get_or_404(id_pedido)
    if not pedido.id_factura:
        return jsonify({'error': 'El pedido no tiene factura aún. Genera la factura primero.'}), 400
    if not pedido.email_cliente:
        return jsonify({'error': 'El pedido no tiene email de cliente registrado.'}), 400

    factura  = Factura.query.get_or_404(pedido.id_factura)
    detalles = list(factura.detalles)
    try:
        ok = enviar_email_factura(pedido.email_cliente, factura, detalles)
        if ok:
            return jsonify({'ok': True, 'mensaje': f'Email enviado a {pedido.email_cliente}'}), 200
        else:
            return jsonify({'error': 'No se pudo enviar el email. Verifica las credenciales SMTP en Render.'}), 500
    except Exception as e:
        logger.error('[REENVIAR-EMAIL] Error: %s', str(e), exc_info=True)
        return jsonify({'error': 'No se pudo reenviar el email'}), 500


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/actualizar-entrega', methods=['POST'])
@jwt_required()
def actualizar_estado_entrega(id_pedido):
    """Actualiza el estado de entrega de un pedido pagado (POR_ENTREGAR → EMPACADO → ENTREGADO)."""
    pedido = PedidoWeb.query.get_or_404(id_pedido)
    if not pedido.id_factura:
        return jsonify({'error': 'El pedido no tiene factura aún'}), 400

    data = request.get_json() or {}
    nuevo_estado = data.get('estado_entrega', '').upper()
    estados_validos = ['POR_ENTREGAR', 'EMPACADO', 'ENTREGADO']
    if nuevo_estado not in estados_validos:
        return jsonify({'error': f'Estado inválido. Use: {", ".join(estados_validos)}'}), 400

    factura = Factura.query.get(pedido.id_factura)
    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    factura.estado_entrega = nuevo_estado
    if nuevo_estado == 'ENTREGADO' and not factura.fecha_entrega:
        from datetime import date as _date
        factura.fecha_entrega = _date.today()
    db.session.commit()

    # Aviso por WhatsApp según el nuevo estado (no bloquea)
    if pedido.telefono_cliente:
        if nuevo_estado == 'EMPACADO':
            # Si viene de fabricación, el aviso ya lo envió marcar_listo() con el link de saldo.
            pf = PedidoFabricacion.query.filter_by(id_pedido_web=pedido.id_pedido).first()
            if not pf or pf.estado != 'listo_para_entrega':
                notificar_whatsapp(pedido.telefono_cliente, 'pedido_listo', {
                    'nombre': pedido.nombre_cliente, 'referencia': pedido.referencia,
                })
        elif nuevo_estado == 'ENTREGADO':
            notificar_whatsapp(pedido.telefono_cliente, 'entregado', {
                'nombre': pedido.nombre_cliente, 'referencia': pedido.referencia,
            })

    return jsonify({
        'ok': True,
        'estado_entrega': nuevo_estado,
        'pedido': pedido.to_dict(),
    }), 200


@tienda_bp.route('/admin/pedidos/<int:id_pedido>/factura.pdf', methods=['GET'])
@jwt_required()
def descargar_factura_admin(id_pedido):
    """Genera y descarga el PDF de la factura de un pedido. Requiere JWT."""
    from flask import Response
    from app.utils.email_service import generar_pdf_factura

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
# ADMIN — Pedidos de Fabricación
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/admin/fabricacion/pedidos', methods=['GET'])
@jwt_required()
def listar_pedidos_fabricacion():
    estado = request.args.get('estado', '').strip()
    limit  = min(request.args.get('limit', 50, type=int), 200)
    offset = request.args.get('offset', 0, type=int)

    q = PedidoFabricacion.query
    if estado:
        q = q.filter(PedidoFabricacion.estado == estado)
    q = q.order_by(PedidoFabricacion.fecha_pedido.desc())

    total   = q.count()
    pedidos = q.offset(offset).limit(limit).all()
    return jsonify({'pedidos': [p.to_dict() for p in pedidos], 'total': total}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>', methods=['GET'])
@jwt_required()
def detalle_pedido_fabricacion(id_pedido):
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    return jsonify({'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/marcar-listo', methods=['POST'])
@jwt_required()
def marcar_pedido_fabricacion_listo(id_pedido):
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    if pf.estado == 'entregado':
        return jsonify({'error': 'El pedido ya fue entregado'}), 400
    pf.estado = 'listo_para_entrega'
    db.session.commit()

    # Avisar al cliente que su pedido está listo. Si debe saldo, generar el
    # link de MercadoPago y mandárselo en el mismo mensaje de WhatsApp.
    saldo = pf.saldo_pendiente or 0
    pago_url = None
    referencia = None
    pedido = PedidoWeb.query.get(pf.id_pedido_web) if pf.id_pedido_web else None
    if pedido:
        referencia = pedido.referencia
        if saldo > 0 and pedido.id_factura:
            factura = Factura.query.get(pedido.id_factura)
            if factura:
                pago_url = _generar_link_saldo(pedido, factura)

    if pf.telefono_cliente:
        datos = {'nombre': pf.nombre_cliente, 'referencia': referencia or ''}
        if saldo > 0:
            datos['saldo'] = f"${int(saldo):,}".replace(',', '.')
            if pago_url:
                datos['pago_url'] = pago_url
        notificar_whatsapp(pf.telefono_cliente, 'pedido_listo', datos)

    registrar_auditoria('pedidos_fabricacion', pf.id_pedido, 'MARCAR_LISTO',
                        f'Pedido {referencia or pf.id_pedido} listo para entrega'
                        + (f'; saldo pendiente ${int(saldo)}' if saldo > 0 else ''))
    return jsonify({'ok': True, 'estado': pf.estado, 'pago_url': pago_url, 'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/marcar-entregado', methods=['POST'])
@jwt_required()
def marcar_pedido_fabricacion_entregado(id_pedido):
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    pf.estado = 'entregado'
    db.session.commit()
    registrar_auditoria('pedidos_fabricacion', pf.id_pedido, 'MARCAR_ENTREGADO',
                        f'Pedido de fabricación {pf.id_pedido} marcado como entregado')
    return jsonify({'ok': True, 'estado': pf.estado, 'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/marcar-notificado', methods=['POST'])
@jwt_required()
def marcar_pedido_fabricacion_notificado(id_pedido):
    """Marca que el cliente fue notificado por WhatsApp"""
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    pf.notificado = True
    db.session.commit()
    return jsonify({'ok': True, 'notificado': True}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/registrar-saldo', methods=['POST'])
@jwt_required()
def registrar_saldo_fabricacion(id_pedido):
    """Registra el pago del saldo pendiente de un pedido de fabricación"""
    data   = request.get_json() or {}
    monto  = float(data.get('monto', 0))
    metodo = data.get('metodo', 'efectivo')

    if monto <= 0:
        return jsonify({'error': 'El monto debe ser mayor a 0'}), 400

    pf = PedidoFabricacion.query.get_or_404(id_pedido)

    if pf.saldo_pendiente <= 0:
        return jsonify({'error': 'Este pedido no tiene saldo pendiente'}), 400

    monto = min(monto, pf.saldo_pendiente)
    pf.saldo_pendiente = round(max(0, pf.saldo_pendiente - monto), 2)
    pf.abono_monto     = round(pf.abono_monto + monto, 2)

    # Actualizar factura y pedido_web asociados
    pedido_web = PedidoWeb.query.get(pf.id_pedido_web) if pf.id_pedido_web else None
    if pedido_web and pedido_web.id_factura:
        factura = Factura.query.get(pedido_web.id_factura)
        if factura:
            factura.saldo_pendiente = max(0, (factura.saldo_pendiente or 0) - monto)
            factura.total_abonado   = (factura.total_abonado or 0) + monto
            if factura.saldo_pendiente <= 0:
                factura.estado = 'PAGADA'
                if pedido_web:
                    pedido_web.estado = 'pagado'
            # Registrar el pago
            db.session.add(Pago(
                id_factura=factura.id_factura,
                valor=monto,
                metodo_pago=metodo.upper(),
                usuario_registro='POS',
                fecha_pago=date.today(),
            ))

    db.session.commit()
    registrar_auditoria('pedidos_fabricacion', pf.id_pedido, 'REGISTRAR_SALDO',
                        f'Saldo pagado ${monto:.0f} ({metodo}); restante ${pf.saldo_pendiente:.0f}')
    return jsonify({'ok': True, 'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/actualizar-fecha', methods=['POST'])
@jwt_required()
def actualizar_fecha_fabricacion(id_pedido):
    """Actualiza la fecha estimada de entrega"""
    data = request.get_json() or {}
    fecha_str = data.get('fecha_estimada', '')
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    if fecha_str:
        try:
            pf.fecha_estimada = date.fromisoformat(fecha_str)
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400
    db.session.commit()

    # Aviso por WhatsApp al cliente con la fecha estimada (no bloquea)
    if pf.telefono_cliente and pf.fecha_estimada:
        notificar_whatsapp(pf.telefono_cliente, 'fecha_entrega', {
            'nombre': pf.nombre_cliente,
            'fecha': pf.fecha_estimada.strftime('%d/%m/%Y'),
        })

    return jsonify({'ok': True, 'fecha_estimada': pf.fecha_estimada.isoformat() if pf.fecha_estimada else None}), 200


@tienda_bp.route('/admin/fabricacion/stock-pendiente', methods=['GET'])
@jwt_required()
def listar_stock_pendiente():
    items = StockPendienteFabricacion.query.filter_by(estado='pendiente')\
        .order_by(StockPendienteFabricacion.fecha_creacion.asc()).all()
    return jsonify({'items': [i.to_dict() for i in items]}), 200


@tienda_bp.route('/admin/fabricacion/stock-pendiente/registrar', methods=['POST'])
@jwt_required()
def registrar_fabricacion():
    """Registra unidades fabricadas: suma stock real y actualiza pedidos afectados"""
    data        = request.get_json() or {}
    id_pendiente = data.get('id_pendiente')
    cantidad_fab = int(data.get('cantidad_fabricada', 0))
    if not id_pendiente or cantidad_fab <= 0:
        return jsonify({'error': 'Datos incompletos'}), 400

    spf = StockPendienteFabricacion.query.get_or_404(id_pendiente)

    # 1. Sumar al stock real
    stock = Stock.query.filter_by(
        id_colegio=spf.id_colegio,
        id_producto=spf.id_producto,
        talla_individual=spf.talla,
    ).first()
    if stock:
        stock.cantidad += cantidad_fab
    else:
        db.session.add(Stock(
            id_colegio=spf.id_colegio,
            id_producto=spf.id_producto,
            talla_individual=spf.talla,
            cantidad=cantidad_fab,
        ))

    # 2. Reducir pendiente o marcar completado
    spf.cantidad_pendiente = max(0, spf.cantidad_pendiente - cantidad_fab)
    if spf.cantidad_pendiente == 0:
        spf.estado = 'completado'

    # 3. Actualizar pedidos de fabricación afectados → listo_para_entrega
    if spf.ids_pedidos:
        ids = [int(x) for x in spf.ids_pedidos.split(',') if x.strip().isdigit()]
        for pid in ids:
            pf = PedidoFabricacion.query.get(pid)
            if pf and pf.estado == 'en_produccion':
                # Verificar si todos sus items ya están listos
                items_pf = json.loads(pf.items_json) if pf.items_json else []
                todos_listos = True
                for item in items_pf:
                    spf_item = StockPendienteFabricacion.query.filter_by(
                        id_colegio=pf.id_colegio,
                        id_producto=item['id_producto'],
                        talla=item['talla'],
                        estado='pendiente',
                    ).first()
                    if spf_item and spf_item.cantidad_pendiente > 0:
                        todos_listos = False
                        break
                if todos_listos:
                    pf.estado = 'listo_para_entrega'

    db.session.commit()
    return jsonify({'ok': True, 'cantidad_pendiente': spf.cantidad_pendiente}), 200


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

def _clasificar_item(id_colegio, id_producto, talla, cantidad, id_reserva, ahora):
    """
    Clasifica un item server-side ignorando lo que envíe el frontend.
    Retorna (tipo_pedido, stock_disponible_para_deducir).

    Tipos:
      'normal'      → todo el stock disponible (reserva válida o stock libre)
      'mixto'       → parte de la cantidad tiene stock, el resto va a fabricación
      'fabricacion' → sin stock, va directo a fabricación
    """
    # Reserva válida que cubre la cantidad solicitada → normal
    if id_reserva:
        reserva = Reserva.query.get(id_reserva)
        if reserva and reserva.estado == 'activa' and reserva.fecha_expiracion >= ahora:
            if reserva.cantidad >= cantidad:
                return 'normal', cantidad
            # Reserva cubre menos de lo pedido → mixto
            return 'mixto', reserva.cantidad

    # Sin reserva válida: verificar stock fresco en la DB
    stock = Stock.query.filter_by(
        id_colegio=id_colegio,
        id_producto=id_producto,
        talla_individual=talla,
    ).first()
    stock_bruto = stock.cantidad if stock else 0

    reservas_activas = db.session.query(
        func.coalesce(func.sum(Reserva.cantidad), 0)
    ).filter(
        Reserva.id_colegio == id_colegio,
        Reserva.id_producto == id_producto,
        Reserva.talla == talla,
        Reserva.estado == 'activa',
        Reserva.fecha_expiracion > ahora,
    ).scalar() or 0

    stock_disp = max(0, stock_bruto - reservas_activas)

    if stock_disp >= cantidad:
        return 'normal', cantidad
    elif stock_disp > 0:
        return 'mixto', stock_disp
    else:
        return 'fabricacion', 0


def _lanzar_email_async(email_cliente, factura_id):
    """Envía el email de factura en un hilo daemon para no bloquear el webhook."""
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            try:
                factura = Factura.query.get(factura_id)
                if factura:
                    detalles = list(factura.detalles)
                    enviar_email_factura(email_cliente, factura, detalles)
                    logger.info('[EMAIL-ASYNC] Enviado a %s (factura %s)', email_cliente, factura_id)
            except Exception as exc:
                logger.error('[EMAIL-ASYNC] Error: %s', str(exc))

    threading.Thread(target=_run, daemon=True).start()


def _crear_factura_desde_pedido(pedido: PedidoWeb) -> Factura:
    """Convierte un PedidoWeb pagado en una Factura del sistema"""
    items = json.loads(pedido.items_json)

    # Separar items: normal/mixto (tienen algo de stock) vs fabricacion puro
    items_normales = [i for i in items if i.get('tipo_pedido') not in ('fabricacion',)]
    items_fab      = [i for i in items if i.get('tipo_pedido') == 'fabricacion']

    # Totales
    total_normal = sum(i['subtotal'] for i in items_normales)
    total_fab    = sum(i['subtotal'] for i in items_fab)
    total_orden  = total_normal + total_fab

    # Abono pagado (lo que registró MercadoPago = pedido.total)
    abono_pagado    = pedido.total
    saldo_pendiente = max(0, total_orden - abono_pagado)

    serie = SerieFacturacion.query.filter_by(activa=True).first()
    if not serie:
        # Auto-crear serie si no existe (primera vez que se usa el sistema)
        from datetime import datetime as _dt_now
        serie = SerieFacturacion(
            prefijo='FAC',
            ano=_dt_now.utcnow().year,
            consecutivo_actual=0,
            formato='FAC-{ano}-{consecutivo:06d}',
            activa=True,
        )
        db.session.add(serie)
        db.session.flush()
        logger.info('[FACTURA] Serie de facturación auto-creada para el año %s', serie.ano)
    serie.consecutivo_actual += 1
    formato = serie.formato or 'FAC-{ano}-{consecutivo:06d}'
    numero = formato.format(ano=serie.ano, consecutivo=serie.consecutivo_actual)

    cliente = Cliente.query.filter_by(email=pedido.email_cliente).first()
    if not cliente and pedido.documento_cliente:
        cliente = Cliente.query.filter_by(numero_documento=pedido.documento_cliente).first()
    if not cliente:
        cliente = Cliente(
            nombre=pedido.nombre_cliente,
            telefono=pedido.telefono_cliente,
            email=pedido.email_cliente,
            numero_documento=pedido.documento_cliente or '',
        )
        db.session.add(cliente)
        db.session.flush()

    obs_fab = ' [INCLUYE PEDIDO POR FABRICACIÓN]' if items_fab else ''
    factura = Factura(
        numero_factura=numero,
        id_colegio=pedido.id_colegio,
        cliente_nombre=pedido.nombre_cliente,
        cliente_telefono=pedido.telefono_cliente,
        cliente_email=pedido.email_cliente,
        cliente_nit=pedido.documento_cliente or '',
        cliente_direccion=getattr(pedido, 'direccion_envio', '') or '',
        fecha_factura=date.today(),
        total=total_orden,
        subtotal=total_orden,
        total_abonado=abono_pagado,
        saldo_pendiente=saldo_pendiente,
        estado='PAGADA' if saldo_pendiente == 0 else 'ABONO',
        estado_entrega='POR_ENTREGAR',
        metodo_pago=pedido.metodo_pago or 'MP',
        observaciones=f'Pedido web #{pedido.referencia}{obs_fab}',
        usuario_creacion='TIENDA_WEB',
    )
    db.session.add(factura)
    db.session.flush()

    # ═══════════════════════════════════════════════════════════════
    # MEJORA #1: SELECT FOR UPDATE para evitar race conditions
    #   cuando dos pagos concurrentes intentan descontar el mismo stock.
    # MEJORA #3: Re-verificar stock real al momento del webhook
    #   (entre la creación del pedido y el pago pudieron agotarse).
    #   Si falta stock, se reclasifica dinámicamente a fabricación
    #   y se actualiza pedido.items_json para que el admin panel lo refleje.
    # ═══════════════════════════════════════════════════════════════
    items_actualizados = []
    hubo_cambio_stock = False

    for item in items:
        db.session.add(FacturaDetalle(
            id_factura=factura.id_factura,
            id_producto=item['id_producto'],
            talla_individual=item['talla'],
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario'],
            total_linea=item['subtotal'],
        ))

        tipo_item      = item.get('tipo_pedido', 'normal')
        cantidad       = item['cantidad']
        stock_esperado = cantidad if tipo_item == 'normal' else int(item.get('stock_disponible', 0))

        # FOR UPDATE: bloquea la fila para que otra transacción no la modifique
        stock = Stock.query.with_for_update().filter_by(
            id_colegio=pedido.id_colegio,
            id_producto=item['id_producto'],
            talla_individual=item['talla'],
        ).first()

        stock_real = stock.cantidad if stock else 0

        # Re-verificar cuánto podemos descontar realmente
        cant_descontar = min(stock_esperado, stock_real)

        if stock and cant_descontar > 0:
            stock.cantidad -= cant_descontar

        # Si el stock real es menor al esperado → fabricación para la diferencia
        item_actualizado = dict(item)
        if cant_descontar < cantidad:
            hubo_cambio_stock = True
            faltante = cantidad - cant_descontar
            item_actualizado['tipo_pedido'] = 'mixto' if cant_descontar > 0 else 'fabricacion'
            item_actualizado['stock_disponible'] = cant_descontar
            item_actualizado['stock_real_al_pagar'] = stock_real
            logger.warning(
                '[STOCK-RACE] Producto %s talla %s: esperado=%d real=%d → fabricación=%d',
                item['id_producto'], item['talla'], cantidad, stock_real, faltante
            )
        items_actualizados.append(item_actualizado)

        if item.get('id_reserva'):
            reserva = Reserva.query.get(item['id_reserva'])
            if reserva:
                reserva.estado = 'completada'

    # Si hubo cambios de stock, persistir items_json actualizado
    # para que _crear_pedido_fabricacion_si_aplica() lo vea correctamente
    if hubo_cambio_stock:
        pedido.items_json = json.dumps(items_actualizados)
        pedido.tiene_fabricacion = True
        db.session.flush()

    db.session.add(Pago(
        id_factura=factura.id_factura,
        valor=abono_pagado,
        metodo_pago=pedido.metodo_pago or 'MP',
        usuario_registro='TIENDA_WEB',
        fecha_pago=date.today(),
    ))
    db.session.commit()
    return factura


def _crear_pedido_fabricacion_si_aplica(pedido: PedidoWeb):
    """Si el pedido tiene items de fabricación o mixtos, crea PedidoFabricacion y StockPendienteFabricacion"""
    items = json.loads(pedido.items_json) if pedido.items_json else []

    # Incluir fabricacion puros Y la porción de fabricación de items mixtos
    items_fab = []
    for i in items:
        tp = i.get('tipo_pedido', 'normal')
        if tp == 'fabricacion':
            items_fab.append(i)
        elif tp == 'mixto':
            cant_fab = i['cantidad'] - int(i.get('stock_disponible', 0))
            if cant_fab > 0:
                items_fab.append({**i, 'cantidad': cant_fab, 'subtotal': i['precio_unitario'] * cant_fab})

    if not items_fab:
        return

    total_fab    = sum(i['subtotal'] for i in items_fab)
    total_orden  = sum(i['subtotal'] for i in items)
    abono_porc   = getattr(pedido, 'abono_porcentaje', 100) or 100
    abono_monto  = pedido.total
    saldo        = max(0, total_fab - (abono_monto - (total_orden - total_fab)))

    fecha_estimada = (datetime.utcnow() + timedelta(days=60)).date()

    pf = PedidoFabricacion(
        id_pedido_web=pedido.id_pedido,
        nombre_cliente=pedido.nombre_cliente,
        email_cliente=pedido.email_cliente,
        telefono_cliente=pedido.telefono_cliente,
        id_colegio=pedido.id_colegio,
        nombre_colegio=pedido.nombre_colegio,
        total_orden=total_fab,
        abono_porcentaje=abono_porc,
        abono_monto=abono_monto,
        saldo_pendiente=saldo,
        items_json=json.dumps(items_fab),
        fecha_estimada=fecha_estimada,
        estado='en_produccion',
    )
    try:
        pf.direccion_envio = getattr(pedido, 'direccion_envio', '') or ''
    except Exception:
        pass
    db.session.add(pf)
    db.session.flush()

    # Acumular en stock_pendiente_fabricacion
    for item in items_fab:
        spf = StockPendienteFabricacion.query.filter_by(
            id_colegio=pedido.id_colegio,
            id_producto=item['id_producto'],
            talla=item['talla'],
            estado='pendiente',
        ).first()
        if spf:
            spf.cantidad_pendiente += item['cantidad']
            ids_list = spf.ids_pedidos.split(',') if spf.ids_pedidos else []
            if str(pf.id_pedido) not in ids_list:
                ids_list.append(str(pf.id_pedido))
            spf.ids_pedidos = ','.join(filter(None, ids_list))
        else:
            db.session.add(StockPendienteFabricacion(
                id_colegio=pedido.id_colegio,
                id_producto=item['id_producto'],
                talla=item['talla'],
                cantidad_pendiente=item['cantidad'],
                ids_pedidos=str(pf.id_pedido),
                estado='pendiente',
            ))

    db.session.commit()
