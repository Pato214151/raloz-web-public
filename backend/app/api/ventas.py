"""
API de Ventas / Hoja Diaria de Ventas
═════════════════════════════════════════════════════════════════

Maneja:
  1. Hoja diaria de ventas: facturas, pagos, gastos
  2. Resumen por método de pago
  3. Cálculo de ingresos y utilidades

Endpoints:
  GET  /ventas/hoja?fecha=YYYY-MM-DD - hoja diaria de ventas
  GET  /ventas/resumen-metodos?fecha_desde=X&fecha_hasta=Y - resumen por método de pago
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, Pago, Gasto
from app.utils.decorators import rol_requerido
from app.utils.validators import validate_date
from datetime import date, datetime, timedelta
from sqlalchemy import func

ventas_bp = Blueprint('ventas', __name__)

# Métodos de pago válidos
METODOS_PAGO = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']


@ventas_bp.route('/hoja', methods=['GET'])
@jwt_required()
def hoja_ventas_diaria():
    """
    Obtener hoja de ventas de un día.

    Query params:
      - fecha (str, format YYYY-MM-DD): fecha de la hoja (default: hoy)

    Response:
      {
        "fecha": "2026-02-28",
        "resumen": {
          "total_facturas": 10,
          "total_ventas": 1500000,
          "total_cobrado": 1300000,
          "total_gastos": 150000,
          "utilidad": 1150000,
          "saldo_pendiente": 200000
        },
        "facturas": [
          {
            "numero_factura": "FAC-2026-000001",
            "cliente_nombre": "Juan Pérez",
            "colegio_nombre": "Colegio A",
            "total": 150000,
            "estado": "PAGADA",
            "metodo_pago": "EFECTIVO"
          },
          ...
        ],
        "pagos": [
          {
            "id_pago": 1,
            "numero_factura": "FAC-2026-000001",
            "valor": 150000,
            "metodo": "EFECTIVO",
            "fecha": "2026-02-28"
          },
          ...
        ],
        "gastos": [
          {
            "id_gasto": 1,
            "descripcion": "Combustible",
            "valor": 50000,
            "categoria": "TRANSPORTE",
            "fecha": "2026-02-28"
          },
          ...
        ]
      }
    """
    fecha_str = request.args.get('fecha', date.today().isoformat())
    fecha_hasta_str = request.args.get('fecha_hasta', fecha_str)

    fecha = validate_date(fecha_str)
    fecha_hasta = validate_date(fecha_hasta_str) or fecha

    if not fecha:
        return jsonify({'error': f'Fecha inválida: {fecha_str}'}), 400

    # Facturas del rango
    facturas = Factura.query.filter(
        Factura.fecha_factura >= fecha,
        Factura.fecha_factura <= fecha_hasta,
        Factura.estado != 'ANULADA'
    ).order_by(Factura.numero_factura).all()

    # Pagos del rango
    pagos = Pago.query.filter(
        Pago.fecha_pago >= fecha,
        Pago.fecha_pago <= fecha_hasta
    ).order_by(Pago.fecha_pago).all()

    # Gastos del rango (excluye deudas pendientes)
    gastos = Gasto.query.filter(
        Gasto.fecha >= fecha,
        Gasto.fecha <= fecha_hasta,
        func.coalesce(Gasto.estado_pago, 'PAGADO') != 'PENDIENTE',
    ).order_by(Gasto.fecha).all()

    # Calcular totales
    total_ventas = sum(f.total for f in facturas)
    total_ingresos = sum(p.valor for p in pagos)
    total_gastos_val = sum(g.valor for g in gastos)
    saldo_pendiente = sum(f.saldo_pendiente or 0 for f in facturas)
    utilidad = total_ingresos - total_gastos_val

    # Agrupar pagos por método
    por_metodo_dict = {}
    for p in pagos:
        m = p.metodo_pago or 'EFECTIVO'
        if m not in por_metodo_dict:
            por_metodo_dict[m] = {'metodo': m, 'total': 0, 'cantidad': 0}
        por_metodo_dict[m]['total'] += p.valor
        por_metodo_dict[m]['cantidad'] += 1

    resumen = {
        'total_facturas': len(facturas),
        'total_ventas': total_ventas,
        'total_ingresos': total_ingresos,
        'total_cobrado': total_ingresos,
        'total_pagos': len(pagos),
        'total_gastos': total_gastos_val,
        'num_gastos': len(gastos),
        'utilidad': utilidad,
        'saldo_pendiente': saldo_pendiente,
    }

    facturas_data = [{
        'numero_factura': f.numero_factura,
        'cliente_nombre': f.cliente_nombre,
        'colegio_nombre': f.colegio.nombre if f.colegio else None,
        'total': f.total,
        'estado': f.estado,
        'metodo_pago': f.metodo_pago,
        'fecha': f.fecha_factura.isoformat() if f.fecha_factura else None,
    } for f in facturas]

    pagos_data = [{
        'id_pago': p.id_pago,
        'numero_factura': p.factura.numero_factura if p.factura else None,
        'cliente_nombre': p.factura.cliente_nombre if p.factura else None,
        'valor': p.valor,
        'metodo_pago': p.metodo_pago,
        'fecha_pago': p.fecha_pago.isoformat() if p.fecha_pago else None,
    } for p in pagos]

    gastos_data = [{
        'id_gasto': g.id_gasto,
        'descripcion': g.descripcion,
        'valor': g.valor,
        'metodo_pago': g.metodo_pago,
        'categoria': g.categoria or 'Otros',
        'fecha': g.fecha.isoformat() if g.fecha else None,
    } for g in gastos]

    return jsonify({
        'fecha': fecha.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'resumen': resumen,
        'por_metodo': list(por_metodo_dict.values()),
        'facturas': facturas_data,
        'pagos': pagos_data,
        'gastos': gastos_data,
    }), 200


@ventas_bp.route('/resumen-metodos', methods=['GET'])
@jwt_required()
def resumen_pagos_metodos():
    """
    Resumen de pagos agrupados por método.

    Query params:
      - fecha_desde (str, format YYYY-MM-DD): fecha inicial
      - fecha_hasta (str, format YYYY-MM-DD): fecha final
      - colegio_id (int, opcional): filtrar por colegio

    Response:
      {
        "fecha_desde": "2026-02-01",
        "fecha_hasta": "2026-02-28",
        "resumen_general": {
          "total_cobrado": 1500000,
          "total_pendiente": 300000,
          "total_anulado": 50000
        },
        "por_metodo": [
          {
            "metodo": "EFECTIVO",
            "total": 800000,
            "cantidad": 5,
            "porcentaje": 53.3
          },
          {
            "metodo": "NEQUI",
            "total": 500000,
            "cantidad": 8,
            "porcentaje": 33.3
          },
          ...
        ],
        "por_colegio": [
          {
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "total_cobrado": 600000,
            "total_pendiente": 150000,
            "efectivo": 400000,
            "nequi": 200000,
            "daviplata": 0,
            "bancolombia": 0,
            "transferencia": 0
          },
          ...
        ]
      }
    """
    fecha_desde_str = request.args.get('fecha_desde')
    fecha_hasta_str = request.args.get('fecha_hasta')
    colegio_id = request.args.get('colegio_id', type=int)

    if not fecha_desde_str or not fecha_hasta_str:
        return jsonify({'error': 'fecha_desde y fecha_hasta son requeridas'}), 400

    fecha_desde = validate_date(fecha_desde_str)
    fecha_hasta = validate_date(fecha_hasta_str)

    if not fecha_desde or not fecha_hasta:
        return jsonify({'error': 'Fechas inválidas'}), 400

    # Consulta base de pagos
    query_pagos = Pago.query.filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    )

    # Consulta base de facturas
    query_facturas = Factura.query.filter(
        Factura.fecha_factura >= fecha_desde,
        Factura.fecha_factura <= fecha_hasta
    )

    if colegio_id:
        query_pagos = query_pagos.join(Factura).filter(Factura.id_colegio == colegio_id)
        query_facturas = query_facturas.filter(Factura.id_colegio == colegio_id)

    # Resumen general
    total_cobrado = db.session.query(func.sum(Pago.valor)).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    ).scalar() or 0

    facturas_filtradas = query_facturas.all()
    total_pendiente = sum(f.saldo_pendiente or 0 for f in facturas_filtradas
                         if f.estado == 'PENDIENTE')
    total_anulado = sum(f.total for f in facturas_filtradas if f.estado == 'ANULADA')

    resumen_general = {
        'total_cobrado': float(total_cobrado),
        'total_pendiente': float(total_pendiente),
        'total_anulado': float(total_anulado),
    }

    # Por método
    pagos_por_metodo = db.session.query(
        Pago.metodo_pago,
        func.sum(Pago.valor).label('total'),
        func.count(Pago.id_pago).label('cantidad'),
    ).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    ).group_by(Pago.metodo_pago).all()

    por_metodo = []
    for metodo, total, cantidad in pagos_por_metodo:
        porcentaje = (float(total) / float(total_cobrado) * 100) if total_cobrado > 0 else 0
        por_metodo.append({
            'metodo': metodo,
            'total': float(total),
            'cantidad': cantidad,
            'porcentaje': round(porcentaje, 1),
        })

    # Por colegio
    colegios = Factura.query.filter(
        Factura.fecha_factura >= fecha_desde,
        Factura.fecha_factura <= fecha_hasta
    ).distinct(Factura.id_colegio).with_entities(Factura.id_colegio).all()

    por_colegio = []
    for (colegio_id_row,) in colegios:
        facturas_colegio = Factura.query.filter(
            Factura.id_colegio == colegio_id_row,
            Factura.fecha_factura >= fecha_desde,
            Factura.fecha_factura <= fecha_hasta
        ).all()

        pagos_colegio = Pago.query.join(Factura).filter(
            Factura.id_colegio == colegio_id_row,
            Pago.fecha_pago >= fecha_desde,
            Pago.fecha_pago <= fecha_hasta
        ).all()

        colegio_obj = db.session.query(db.Model.metadata.tables['colegios']).filter(
            db.Model.metadata.tables['colegios'].c.id_colegio == colegio_id_row
        ).first()

        total_cobrado_colegio = sum(p.valor for p in pagos_colegio)
        total_pendiente_colegio = sum(f.saldo_pendiente or 0 for f in facturas_colegio
                                      if f.estado == 'PENDIENTE')

        # Desglose por método
        metodos_dict = {m: 0 for m in METODOS_PAGO}
        for pago in pagos_colegio:
            if pago.metodo_pago in metodos_dict:
                metodos_dict[pago.metodo_pago] += pago.valor

        entry = {
            'id_colegio': colegio_id_row,
            'colegio_nombre': facturas_colegio[0].colegio.nombre if facturas_colegio and facturas_colegio[0].colegio else None,
            'total_cobrado': float(total_cobrado_colegio),
            'total_pendiente': float(total_pendiente_colegio),
        }
        entry.update({m.lower(): float(v) for m, v in metodos_dict.items()})
        por_colegio.append(entry)

    return jsonify({
        'fecha_desde': fecha_desde.isoformat(),
        'fecha_hasta': fecha_hasta.isoformat(),
        'resumen_general': resumen_general,
        'por_metodo': por_metodo,
        'por_colegio': por_colegio,
    }), 200
