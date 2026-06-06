"""
Centro de Operaciones — vista unificada del proceso de preparación/entrega.

Junta en un solo tablero las 3 "pistas" que hoy están separadas:
  - Prendas pendientes (ventas del local por entregar)
  - Pedidos de fabricación (en producción / listos)
  - Pedidos web (por entregar / empacados)

Normaliza todo a etapas: por_preparar → listo (para entregar).
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models import PrendaPendiente, PedidoFabricacion, Factura

operaciones_bp = Blueprint('operaciones', __name__)


def _money(n):
    return '$' + f'{int(n or 0):,}'.replace(',', '.')


@operaciones_bp.route('/tablero', methods=['GET'])
@jwt_required()
def tablero():
    items = []

    # 1) Prendas pendientes (venta en el local, falta entregar)
    for p in (PrendaPendiente.query
              .filter_by(estado='PENDIENTE')
              .order_by(PrendaPendiente.fecha_registro).limit(300).all()):
        items.append({
            'tipo': 'local', 'etapa': 'por_preparar',
            'id': f'local-{p.id_pendiente}',
            'titulo': f'{p.producto_nombre} · {p.talla}',
            'cliente': p.cliente_nombre, 'colegio': p.colegio_nombre,
            'detalle': f'x{p.cantidad}',
            'fecha': p.fecha_registro.isoformat() if p.fecha_registro else None,
            'link': f'/buscar?ver={p.id_factura}' if p.id_factura else '/pendientes',
        })

    # 2) Pedidos de fabricación (en producción o listos)
    for f in (PedidoFabricacion.query
              .filter(PedidoFabricacion.estado.in_(['en_produccion', 'listo_para_entrega']))
              .order_by(PedidoFabricacion.fecha_pedido).limit(300).all()):
        etapa = 'listo' if f.estado == 'listo_para_entrega' else 'por_preparar'
        detalle = f'saldo {_money(f.saldo_pendiente)}' if (f.saldo_pendiente or 0) > 0 else 'pagado'
        items.append({
            'tipo': 'fabricacion', 'etapa': etapa,
            'id': f'fab-{f.id_pedido}',
            'titulo': f'Fabricación #{f.id_pedido}',
            'cliente': f.nombre_cliente, 'colegio': f.nombre_colegio,
            'detalle': detalle,
            'fecha': f.fecha_pedido.isoformat() if f.fecha_pedido else None,
            'link': '/fabricacion',
        })

    # 3) Pedidos web (factura canal WEB por entregar / empacada)
    for fa in (Factura.query
               .filter(Factura.canal == 'WEB',
                       Factura.estado_entrega.in_(['POR_ENTREGAR', 'EMPACADO']),
                       Factura.estado != 'ANULADA')
               .order_by(Factura.fecha_factura).limit(300).all()):
        etapa = 'listo' if fa.estado_entrega == 'EMPACADO' else 'por_preparar'
        items.append({
            'tipo': 'web', 'etapa': etapa,
            'id': f'web-{fa.id_factura}',
            'titulo': f'Pedido web {fa.numero_factura}',
            'cliente': fa.cliente_nombre,
            'colegio': fa.colegio.nombre if fa.colegio else None,
            'detalle': fa.estado_entrega,
            'fecha': fa.fecha_factura.isoformat() if fa.fecha_factura else None,
            'link': '/pedidos-online',
        })

    por_preparar = [i for i in items if i['etapa'] == 'por_preparar']
    listo = [i for i in items if i['etapa'] == 'listo']
    return jsonify({
        'por_preparar': por_preparar,
        'listo': listo,
        'totales': {
            'por_preparar': len(por_preparar),
            'listo': len(listo),
            'total': len(items),
        },
    }), 200
