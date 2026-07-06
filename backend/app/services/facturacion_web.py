"""
Lógica de negocio de la tienda web (RALOZ COL SAS).

Clasificación de items, creación de la factura desde un pedido pagado y
generación de los pedidos de fabricación. Extraído de app/api/tienda.py para
separar la lógica de negocio de las rutas. Lo usan tanto los endpoints
públicos (webhook) como los admin (marcar pagado / generar factura).
"""
import json
import logging
import threading
from datetime import datetime, date, timedelta

from sqlalchemy import func
from flask import current_app

from app import db
from app.utils.email_service import enviar_email_factura
from app.utils.inventario import registrar_movimiento
from app.models import (
    Stock, PedidoWeb, Factura, FacturaDetalle, Pago,
    SerieFacturacion, Cliente, Reserva,
    PedidoFabricacion, StockPendienteFabricacion,
)

logger = logging.getLogger(__name__)


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

        # Re-verificar cuánto podemos descontar realmente. La SALIDA pasa por
        # el kardex (la fila ya quedó bloqueada por el FOR UPDATE de arriba).
        cant_descontar = min(stock_esperado, stock_real)

        if stock and cant_descontar > 0:
            registrar_movimiento(
                pedido.id_colegio, item['id_producto'], item['talla'],
                'SALIDA', cant_descontar,
                usuario='TIENDA_WEB', motivo='Venta web', referencia=numero,
            )

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
