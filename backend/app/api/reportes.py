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
@rol_requerido('administrador')
def reporte_ventas():
    """Reporte de ventas por período"""
    from app.utils.validators import validate_date

    fecha_desde = validate_date(request.args.get('fecha_desde', date.today().replace(day=1).isoformat()))
    fecha_hasta = validate_date(request.args.get('fecha_hasta', date.today().isoformat()))

    if not fecha_desde or not fecha_hasta:
        return jsonify({'error': 'Fechas inválidas'}), 400

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
@rol_requerido('administrador')
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
    # Filtrar directamente en DB por saldo > 0 — evita cargar todas las facturas
    facturas = Factura.query.filter(
        Factura.estado != 'ANULADA',
        Factura.estado != 'CANCELADA',
        Factura.saldo_pendiente > 0.5,
    ).order_by(Factura.fecha_factura.desc()).all()

    resultado = []
    for f in facturas:
        resultado.append({
            **f.to_dict(),
            'total_pagado': round(f.total_abonado or 0, 2),
            'saldo': round(f.saldo_pendiente, 2),
        })

    total_por_cobrar = sum(r['saldo'] for r in resultado)

    return jsonify({
        'cuentas': resultado,
        'total_por_cobrar': round(total_por_cobrar, 2),
        'total_cuentas': len(resultado),
    }), 200


@reportes_bp.route('/cuentas', methods=['GET'])
@rol_requerido('administrador')
def reporte_cuentas():
    """
    Reporte detallado de cuentas (ingresos y egresos).

    Query params:
      - fecha_desde (str, format YYYY-MM-DD): fecha inicial
      - fecha_hasta (str, format YYYY-MM-DD): fecha final
      - colegio_id (int, opcional): filtrar por colegio

    Response:
      {
        "fecha_desde": "2026-02-01",
        "fecha_hasta": "2026-02-28",
        "resumen": {
          "total_ingresos": 1500000,
          "total_gastos": 150000,
          "utilidad_bruta": 1350000,
          "total_cobrado": 1300000,
          "total_pendiente": 200000,
          "utilidad_neta": 1150000
        },
        "detalles_ingresos": {
          "facturas": 1500000,
          "cantidad_facturas": 10,
          "ticket_promedio": 150000
        },
        "detalles_egresos": {
          "gastos": 150000,
          "cantidad_gastos": 5
        },
        "por_colegio": [
          {
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "ingresos": 600000,
            "gastos": 50000,
            "utilidad": 550000,
            "cobrado": 500000,
            "pendiente": 100000
          },
          ...
        ]
      }
    """
    from app.utils.validators import validate_date

    fecha_desde_str = request.args.get('fecha_desde', date.today().replace(day=1).isoformat())
    fecha_hasta_str = request.args.get('fecha_hasta', date.today().isoformat())
    colegio_id = request.args.get('colegio_id', type=int)

    fecha_desde = validate_date(fecha_desde_str)
    fecha_hasta = validate_date(fecha_hasta_str)

    if not fecha_desde or not fecha_hasta:
        return jsonify({'error': 'Fechas inválidas'}), 400

    # Facturas en período
    query_facturas = Factura.query.filter(
        Factura.fecha_factura >= fecha_desde,
        Factura.fecha_factura <= fecha_hasta,
        Factura.estado != 'ANULADA'
    )

    if colegio_id:
        query_facturas = query_facturas.filter(Factura.id_colegio == colegio_id)

    facturas = query_facturas.all()

    # Pagos en período — joinedload para evitar N+1 al acceder pago.factura
    from sqlalchemy.orm import joinedload
    query_pagos = Pago.query.options(joinedload(Pago.factura)).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    )

    if colegio_id:
        query_pagos = query_pagos.join(Factura).filter(Factura.id_colegio == colegio_id)

    pagos = query_pagos.all()

    # Gastos en período
    query_gastos = Gasto.query.filter(
        Gasto.fecha >= fecha_desde,
        Gasto.fecha <= fecha_hasta
    )

    gastos = query_gastos.all()

    # Calcular totales
    total_ingresos = sum(f.total for f in facturas)
    total_gastos = sum(g.valor for g in gastos)
    utilidad_bruta = total_ingresos - total_gastos
    total_cobrado = sum(p.valor for p in pagos)
    total_pendiente = sum(f.saldo_pendiente or 0 for f in facturas if f.estado == 'PENDIENTE')
    utilidad_neta = total_cobrado - total_gastos

    # Detalles de ingresos
    cantidad_facturas = len(facturas)
    ticket_promedio = total_ingresos / cantidad_facturas if cantidad_facturas > 0 else 0

    # Detalles de egresos
    cantidad_gastos = len(gastos)

    # Resumen por colegio
    colegios_dict = {}
    for factura in facturas:
        colegio_id_row = factura.id_colegio
        if colegio_id_row not in colegios_dict:
            colegios_dict[colegio_id_row] = {
                'id_colegio': colegio_id_row,
                'colegio_nombre': factura.colegio.nombre if factura.colegio else None,
                'ingresos': 0,
                'cobrado': 0,
                'pendiente': 0,
                'gastos': 0,
            }
        colegios_dict[colegio_id_row]['ingresos'] += factura.total
        colegios_dict[colegio_id_row]['pendiente'] += factura.saldo_pendiente or 0

    for pago in pagos:
        colegio_id_row = pago.factura.id_colegio if pago.factura else None
        if colegio_id_row and colegio_id_row in colegios_dict:
            colegios_dict[colegio_id_row]['cobrado'] += pago.valor

    for gasto in gastos:
        # Los gastos no tienen colegio asociado típicamente, pero incluir si es necesario
        pass

    por_colegio = list(colegios_dict.values())
    for colegio in por_colegio:
        colegio['utilidad'] = colegio['ingresos'] - colegio['gastos']

    return jsonify({
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'resumen': {
            'total_ingresos': float(total_ingresos),
            'total_gastos': float(total_gastos),
            'utilidad_bruta': float(utilidad_bruta),
            'total_cobrado': float(total_cobrado),
            'total_pendiente': float(total_pendiente),
            'utilidad_neta': float(utilidad_neta),
        },
        'detalles_ingresos': {
            'facturas': float(total_ingresos),
            'cantidad_facturas': cantidad_facturas,
            'ticket_promedio': float(ticket_promedio),
        },
        'detalles_egresos': {
            'gastos': float(total_gastos),
            'cantidad_gastos': cantidad_gastos,
        },
        'por_colegio': por_colegio,
    }), 200


@reportes_bp.route('/ventas-por-colegio', methods=['GET'])
@rol_requerido('administrador')
def ventas_por_colegio():
    """
    Reporte de ventas agrupadas por colegio.

    Query params:
      - fecha_desde (str, format YYYY-MM-DD): fecha inicial
      - fecha_hasta (str, format YYYY-MM-DD): fecha final
      - ordenar (str, default='ventas'): 'ventas', 'facturas' o 'nombre'

    Response:
      {
        "fecha_desde": "2026-02-01",
        "fecha_hasta": "2026-02-28",
        "resumen_general": {
          "total_ventas": 1500000,
          "total_facturas": 15,
          "cantidad_colegios": 8
        },
        "por_colegio": [
          {
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "total_ventas": 600000,
            "cantidad_facturas": 6,
            "ticket_promedio": 100000,
            "total_cobrado": 500000,
            "saldo_pendiente": 100000,
            "estado_cobro": "PARCIAL"
          },
          ...
        ]
      }
    """
    from app.utils.validators import validate_date
    from app.models import Colegio

    fecha_desde_str = request.args.get('fecha_desde', date.today().replace(day=1).isoformat())
    fecha_hasta_str = request.args.get('fecha_hasta', date.today().isoformat())
    ordenar = request.args.get('ordenar', 'ventas').lower()

    fecha_desde = validate_date(fecha_desde_str)
    fecha_hasta = validate_date(fecha_hasta_str)

    if not fecha_desde or not fecha_hasta:
        return jsonify({'error': 'Fechas inválidas'}), 400

    # Agrupar facturas por colegio
    facturas_por_colegio = db.session.query(
        Factura.id_colegio,
        Colegio.nombre,
        func.sum(Factura.total).label('total_ventas'),
        func.count(Factura.id_factura).label('cantidad_facturas'),
        func.sum(Factura.saldo_pendiente).label('saldo_total'),
    ).outerjoin(Colegio).filter(
        Factura.fecha_factura >= fecha_desde,
        Factura.fecha_factura <= fecha_hasta,
        Factura.estado != 'ANULADA'
    ).group_by(Factura.id_colegio, Colegio.nombre).all()

    # Pre-calcular cobrado por colegio en una sola query
    pagos_por_colegio_raw = db.session.query(
        Factura.id_colegio,
        func.coalesce(func.sum(Pago.valor), 0).label('cobrado'),
    ).join(Pago, Pago.id_factura == Factura.id_factura).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta,
    ).group_by(Factura.id_colegio).all()
    pagos_por_colegio = {r.id_colegio: float(r.cobrado) for r in pagos_por_colegio_raw}

    por_colegio = []
    total_ventas_general = 0
    total_facturas_general = 0

    for row in facturas_por_colegio:
        colegio_id = row.id_colegio
        colegio_nombre = row.nombre or f'Colegio {colegio_id}'
        total_ventas = row.total_ventas or 0
        cantidad_facturas = row.cantidad_facturas or 0
        saldo_pendiente = row.saldo_total or 0
        ticket_promedio = total_ventas / cantidad_facturas if cantidad_facturas > 0 else 0

        pagos_colegio = pagos_por_colegio.get(colegio_id, 0.0)

        # Determinar estado de cobro
        if saldo_pendiente > total_ventas * 0.05:  # más de 5% sin cobrar
            estado_cobro = 'PARCIAL'
        elif saldo_pendiente > 0:
            estado_cobro = 'CASI_COMPLETO'
        else:
            estado_cobro = 'COMPLETO'

        por_colegio.append({
            'id_colegio': colegio_id,
            'colegio_nombre': colegio_nombre,
            'total_ventas': float(total_ventas),
            'cantidad_facturas': cantidad_facturas,
            'ticket_promedio': float(ticket_promedio),
            'total_cobrado': float(pagos_colegio),
            'saldo_pendiente': float(saldo_pendiente),
            'estado_cobro': estado_cobro,
        })

        total_ventas_general += total_ventas
        total_facturas_general += cantidad_facturas

    # Ordenar según parámetro
    if ordenar == 'facturas':
        por_colegio = sorted(por_colegio, key=lambda x: x['cantidad_facturas'], reverse=True)
    elif ordenar == 'nombre':
        por_colegio = sorted(por_colegio, key=lambda x: x['colegio_nombre'])
    else:  # ventas (default)
        por_colegio = sorted(por_colegio, key=lambda x: x['total_ventas'], reverse=True)

    return jsonify({
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'resumen_general': {
            'total_ventas': float(total_ventas_general),
            'total_facturas': total_facturas_general,
            'cantidad_colegios': len(por_colegio),
        },
        'por_colegio': por_colegio,
    }), 200
