"""
API de Dashboard
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils.decorators import get_current_identity
from app import db
from app.models import Factura, Pago, Gasto, StockPendiente, PedidoFabricacion, PrendaPendiente, CajaDiaria
from sqlalchemy import func, and_
from datetime import date, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_dashboard():
    """Datos para el dashboard principal"""
    identity = get_current_identity()
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    # Ventas hoy
    ventas_hoy = db.session.query(
        func.count(Factura.id_factura),
        func.coalesce(func.sum(Factura.total), 0),
    ).filter(and_(
        Factura.fecha_factura == hoy,
        Factura.estado != 'ANULADA',
    )).first()

    # Ventas mes
    ventas_mes = db.session.query(
        func.count(Factura.id_factura),
        func.coalesce(func.sum(Factura.total), 0),
    ).filter(and_(
        Factura.fecha_factura >= inicio_mes,
        Factura.fecha_factura <= hoy,
        Factura.estado != 'ANULADA',
    )).first()

    # Cobros hoy
    cobros_hoy = db.session.query(
        func.coalesce(func.sum(Pago.valor), 0),
    ).filter(Pago.fecha_pago == hoy).first()

    # Cobros mes
    cobros_mes = db.session.query(
        func.coalesce(func.sum(Pago.valor), 0),
    ).filter(and_(
        Pago.fecha_pago >= inicio_mes,
        Pago.fecha_pago <= hoy,
    )).first()

    # Gastos mes
    gastos_mes = db.session.query(
        func.coalesce(func.sum(Gasto.valor), 0),
    ).filter(and_(
        Gasto.fecha >= inicio_mes,
        Gasto.fecha <= hoy,
    )).first()

    # Prendas pendientes de entrega (ventas POS con entrega no inmediata)
    pendientes = PrendaPendiente.query.filter_by(estado='PENDIENTE').count()

    # Estado de la caja del día
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    caja_info = {
        'abierta': bool(caja),
        'monto_esperado': float(caja.monto_esperado or 0) if caja else 0,
        'total_ventas': float(caja.total_ventas or 0) if caja else 0,
        'total_gastos': float(caja.total_gastos or 0) if caja else 0,
    }

    # Pedidos web por entregar
    pedidos_web_pendientes = Factura.query.filter(
        Factura.canal == 'WEB',
        Factura.estado_entrega.in_(['POR_ENTREGAR', 'EMPACADO']),
        Factura.estado != 'ANULADA',
    ).count()

    # Fabricación en curso
    fabricacion_en_curso = PedidoFabricacion.query.filter(
        PedidoFabricacion.estado.in_(['en_produccion', 'listo_para_entrega'])
    ).count()

    # Cuentas por cobrar — suma directa en DB sin cargar registros ni pagos
    total_por_cobrar = db.session.query(
        func.coalesce(func.sum(Factura.saldo_pendiente), 0)
    ).filter(
        Factura.estado.in_(['PENDIENTE', 'ABONO'])
    ).scalar() or 0

    # Ventas últimos 7 días — una sola query con GROUP BY
    inicio_7_dias = hoy - timedelta(days=6)
    ventas_7_rango = db.session.query(
        Factura.fecha_factura,
        func.coalesce(func.sum(Factura.total), 0).label('total'),
    ).filter(and_(
        Factura.fecha_factura >= inicio_7_dias,
        Factura.fecha_factura <= hoy,
        Factura.estado != 'ANULADA',
    )).group_by(Factura.fecha_factura).all()

    ventas_por_dia = {r.fecha_factura: float(r.total) for r in ventas_7_rango}
    ventas_7_dias = [
        {
            'fecha': (hoy - timedelta(days=i)).isoformat(),
            'dia': (hoy - timedelta(days=i)).strftime('%a'),
            'total': ventas_por_dia.get(hoy - timedelta(days=i), 0.0),
        }
        for i in range(6, -1, -1)
    ]

    return jsonify({
        'ventas_hoy': {'facturas': ventas_hoy[0], 'total': float(ventas_hoy[1])},
        'ventas_mes': {'facturas': ventas_mes[0], 'total': float(ventas_mes[1])},
        'cobros_hoy': float(cobros_hoy[0]),
        'cobros_mes': float(cobros_mes[0]),
        'gastos_mes': float(gastos_mes[0]),
        'pendientes_entrega': pendientes,
        'pedidos_web_pendientes': pedidos_web_pendientes,
        'fabricacion_en_curso': fabricacion_en_curso,
        'total_por_cobrar': total_por_cobrar,
        'ventas_7_dias': ventas_7_dias,
        'caja': caja_info,
    }), 200
