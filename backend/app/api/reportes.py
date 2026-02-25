"""
API de Reportes y Ventas
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, Pago, Gasto, FacturaDetalle
from app.utils.decorators import rol_requerido
from sqlalchemy import func, and_
from datetime import date, timedelta

reportes_bp = Blueprint('reportes', __name__)


@reportes_bp.route('/ventas', methods=['GET'])
@jwt_required()
def reporte_ventas():
    """Reporte de ventas por período"""
    fecha_desde = request.args.get('fecha_desde', date.today().replace(day=1).isoformat())
    fecha_hasta = request.args.get('fecha_hasta', date.today().isoformat())

    ventas = db.session.query(
        func.count(Factura.id_factura).label('total_facturas'),
        func.sum(Factura.total).label('total_ventas'),
    ).filter(
        and_(
            Factura.fecha_factura >= fecha_desde,
            Factura.fecha_factura <= fecha_hasta,
            Factura.estado != 'ANULADA',
        )
    ).first()

    cobros = db.session.query(
        func.sum(Pago.valor).label('total_cobrado'),
    ).filter(
        and_(
            Pago.fecha_pago >= fecha_desde,
            Pago.fecha_pago <= fecha_hasta,
        )
    ).first()

    gastos_total = db.session.query(
        func.sum(Gasto.valor).label('total_gastos'),
    ).filter(
        and_(
            Gasto.fecha >= fecha_desde,
            Gasto.fecha <= fecha_hasta,
        )
    ).first()

    # Ventas por día
    ventas_diarias = db.session.query(
        Factura.fecha_factura,
        func.count(Factura.id_factura).label('facturas'),
        func.sum(Factura.total).label('total'),
    ).filter(
        and_(
            Factura.fecha_factura >= fecha_desde,
            Factura.fecha_factura <= fecha_hasta,
            Factura.estado != 'ANULADA',
        )
    ).group_by(Factura.fecha_factura).order_by(Factura.fecha_factura).all()

    return jsonify({
        'resumen': {
            'total_facturas': ventas.total_facturas or 0,
            'total_ventas': float(ventas.total_ventas or 0),
            'total_cobrado': float(cobros.total_cobrado or 0),
            'total_gastos': float(gastos_total.total_gastos or 0),
            'utilidad_neta': float((cobros.total_cobrado or 0) - (gastos_total.total_gastos or 0)),
        },
        'ventas_diarias': [{
            'fecha': str(v.fecha_factura),
            'facturas': v.facturas,
            'total': float(v.total),
        } for v in ventas_diarias],
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }), 200


@reportes_bp.route('/productos-mas-vendidos', methods=['GET'])
@jwt_required()
def productos_mas_vendidos():
    """Top productos más vendidos"""
    from app.models import Producto
    limite = request.args.get('limite', 10, type=int)

    top = db.session.query(
        FacturaDetalle.id_producto,
        Producto.nombre,
        func.sum(FacturaDetalle.cantidad).label('total_vendido'),
        func.sum(FacturaDetalle.total_linea).label('total_ingresos'),
    ).join(Producto).join(Factura).filter(
        Factura.estado != 'ANULADA'
    ).group_by(
        FacturaDetalle.id_producto, Producto.nombre
    ).order_by(
        func.sum(FacturaDetalle.cantidad).desc()
    ).limit(limite).all()

    return jsonify({
        'productos': [{
            'id_producto': t.id_producto,
            'nombre': t.nombre,
            'total_vendido': int(t.total_vendido),
            'total_ingresos': float(t.total_ingresos),
        } for t in top]
    }), 200


@reportes_bp.route('/cuentas-por-cobrar', methods=['GET'])
@jwt_required()
def cuentas_por_cobrar():
    """Facturas con saldo pendiente"""
    facturas = Factura.query.filter(
        Factura.estado.in_(['PENDIENTE', 'ABONO'])
    ).order_by(Factura.fecha_factura.desc()).all()

    resultado = []
    for f in facturas:
        pagado = sum(p.valor for p in f.pagos)
        saldo = f.total - pagado
        if saldo > 0:
            resultado.append({
                **f.to_dict(),
                'total_pagado': pagado,
                'saldo': saldo,
            })

    total_por_cobrar = sum(r['saldo'] for r in resultado)

    return jsonify({
        'cuentas': resultado,
        'total_por_cobrar': total_por_cobrar,
        'total_cuentas': len(resultado),
    }), 200
