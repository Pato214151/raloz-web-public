"""
API de Dashboard
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils.decorators import get_current_identity
from app import db
from app.models import Factura, Pago, Gasto, StockPendiente
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

    # Pendientes
    pendientes = StockPendiente.query.filter_by(estado='PENDIENTE').count()

    # Cuentas por cobrar
    from app.models import Factura as F
    facturas_pendientes = Factura.query.filter(
        Factura.estado.in_(['PENDIENTE', 'ABONO'])
    ).all()
    total_por_cobrar = 0
    for f in facturas_pendientes:
        pagado = sum(p.valor for p in f.pagos)
        total_por_cobrar += f.total - pagado

    # Ventas últimos 7 días para gráfica
    ventas_7_dias = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        v = db.session.query(
            func.coalesce(func.sum(Factura.total), 0),
        ).filter(and_(
            Factura.fecha_factura == dia,
            Factura.estado != 'ANULADA',
        )).first()
        ventas_7_dias.append({
            'fecha': dia.isoformat(),
            'dia': dia.strftime('%a'),
            'total': float(v[0]),
        })

    return jsonify({
        'ventas_hoy': {'facturas': ventas_hoy[0], 'total': float(ventas_hoy[1])},
        'ventas_mes': {'facturas': ventas_mes[0], 'total': float(ventas_mes[1])},
        'cobros_hoy': float(cobros_hoy[0]),
        'cobros_mes': float(cobros_mes[0]),
        'gastos_mes': float(gastos_mes[0]),
        'pendientes_entrega': pendientes,
        'total_por_cobrar': total_por_cobrar,
        'ventas_7_dias': ventas_7_dias,
    }), 200
