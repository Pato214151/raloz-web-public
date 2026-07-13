"""
Endpoints de administración de la tienda online — RALOZ COL SAS.
Gestión de pedidos online y de fabricación. Requieren JWT + rol
(administrador o vendedor; ver decoradores en cada endpoint).
"""
import json
import logging
from datetime import datetime, date

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app import db
from app.utils.caja import registrar_ingreso_efectivo
from app.utils.decorators import registrar_auditoria, rol_requerido, get_current_identity
from app.utils.inventario import registrar_movimiento
from app.utils.whatsapp_notify import notificar_whatsapp
from app.utils.email_service import enviar_email_factura
from app.utils.validators import sanitize_string
from app.models import (
    PedidoWeb, Factura, Pago,
    PedidoFabricacion, StockPendienteFabricacion,
    ConfigSitio,
)
from app.services.facturacion_web import (
    _crear_factura_desde_pedido, _crear_pedido_fabricacion_si_aplica,
)
from app.api.tienda import tienda_bp
from app.api.tienda.publico import _generar_link_saldo

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# ADMIN — Gestión de pedidos online (requiere JWT)
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/admin/pedidos/conteo-nuevos', methods=['GET'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def conteo_pedidos_nuevos():
    """Cuenta los pedidos online pagados que aún no se han procesado
    (factura en POR_ENTREGAR). Lo usa el badge de 'pedidos nuevos' del panel."""
    nuevos = (
        PedidoWeb.query
        .join(Factura, PedidoWeb.id_factura == Factura.id_factura)
        .filter(
            PedidoWeb.estado == 'pagado',
            Factura.estado_entrega == 'POR_ENTREGAR',
        )
        .count()
    )
    return jsonify({'nuevos': nuevos}), 200


@tienda_bp.route('/admin/pedidos', methods=['GET'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def listar_pedidos_admin():
    """Lista los pedidos online con filtros. Requiere JWT.
    vista='activos' → solo los que requieren acción (pagados y aún sin entregar),
    ocultando los viejos (entregados, cancelados, fallidos)."""
    estado  = request.args.get('estado', '').strip()
    vista   = request.args.get('vista', '').strip()
    limit   = min(request.args.get('limit', 50, type=int), 200)
    offset  = request.args.get('offset', 0, type=int)

    query = PedidoWeb.query
    if vista == 'activos':
        query = query.join(Factura, PedidoWeb.id_factura == Factura.id_factura).filter(
            PedidoWeb.estado == 'pagado',
            Factura.estado_entrega.in_(['POR_ENTREGAR', 'EMPACADO']),
        )
    elif estado:
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
def detalle_pedido_fabricacion(id_pedido):
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    return jsonify({'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/marcar-listo', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
def marcar_pedido_fabricacion_entregado(id_pedido):
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    pf.estado = 'entregado'
    db.session.commit()
    registrar_auditoria('pedidos_fabricacion', pf.id_pedido, 'MARCAR_ENTREGADO',
                        f'Pedido de fabricación {pf.id_pedido} marcado como entregado')
    return jsonify({'ok': True, 'estado': pf.estado, 'pedido': pf.to_dict()}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/marcar-notificado', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def marcar_pedido_fabricacion_notificado(id_pedido):
    """Marca que el cliente fue notificado por WhatsApp"""
    pf = PedidoFabricacion.query.get_or_404(id_pedido)
    pf.notificado = True
    db.session.commit()
    return jsonify({'ok': True, 'notificado': True}), 200


@tienda_bp.route('/admin/fabricacion/pedidos/<int:id_pedido>/registrar-saldo', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
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

    # Saldo cobrado en efectivo en el local → también entra a la caja abierta
    if metodo.upper() == 'EFECTIVO':
        registrar_ingreso_efectivo(
            f'Saldo fabricación #{pf.id_pedido}', monto, get_current_identity()['usuario'])

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
@rol_requerido('administrador', 'vendedor')
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
@rol_requerido('administrador', 'vendedor')
def listar_stock_pendiente():
    items = StockPendienteFabricacion.query.filter_by(estado='pendiente')\
        .order_by(StockPendienteFabricacion.fecha_creacion.asc()).all()
    return jsonify({'items': [i.to_dict() for i in items]}), 200


@tienda_bp.route('/admin/fabricacion/stock-pendiente/registrar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def registrar_fabricacion():
    """Registra unidades fabricadas: suma stock real y actualiza pedidos afectados"""
    data        = request.get_json() or {}
    id_pendiente = data.get('id_pendiente')
    cantidad_fab = int(data.get('cantidad_fabricada', 0))
    if not id_pendiente or cantidad_fab <= 0:
        return jsonify({'error': 'Datos incompletos'}), 400

    spf = StockPendienteFabricacion.query.get_or_404(id_pendiente)

    # 1. Sumar al stock real — ENTRADA registrada en el kardex
    registrar_movimiento(
        spf.id_colegio, spf.id_producto, spf.talla, 'ENTRADA', cantidad_fab,
        usuario=get_current_identity()['usuario'], motivo='Fabricación',
        referencia=f'SPF-{spf.id_pendiente}',
    )

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
# CONFIG DEL SITIO — banner editable (Fase 1: Publicaciones)
# ══════════════════════════════════════════════════════════════

@tienda_bp.route('/admin/config', methods=['GET'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def obtener_config_admin():
    """Lee la config del sitio para el panel."""
    return jsonify({
        'banner_texto':  ConfigSitio.get('banner_texto', ''),
        'banner_activo': ConfigSitio.get('banner_activo', '1') == '1',
    }), 200


@tienda_bp.route('/admin/config', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_config_admin():
    """Actualiza la config del sitio (solo administrador)."""
    data = request.get_json() or {}
    if 'banner_texto' in data:
        ConfigSitio.set('banner_texto', sanitize_string(data['banner_texto'], 300))
    if 'banner_activo' in data:
        ConfigSitio.set('banner_activo', '1' if data['banner_activo'] else '0')
    db.session.commit()
    return jsonify({'message': 'Configuración actualizada'}), 200
