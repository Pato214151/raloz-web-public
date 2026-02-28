"""
API de Stock Pendiente / Prendas Pendientes
═════════════════════════════════════════════════════════════════

Maneja los items que fueron vendidos pero aún no se han entregado.
Estos pueden ser por:
  1. Stock insuficiente en el momento (StockPendiente)
  2. Prendas que requieren personalización (PrendaPendiente)

Endpoints:
  GET    /pendientes - listar pendientes con filtros
  GET    /pendientes/por-colegio - agrupar por colegio (para costureras)
  GET    /pendientes/resumen - conteo por estado
  POST   /pendientes/<id>/entregar - marcar como entregado
  POST   /pendientes/entregar-lote - entregar múltiples en lote

Roles requeridos:
  - GET: cualquier usuario autenticado
  - POST: administrador, vendedor
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import StockPendiente, PrendaPendiente, Factura
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import validate_required_fields
from datetime import date
from sqlalchemy import func

pendientes_bp = Blueprint('pendientes', __name__)


@pendientes_bp.route('', methods=['GET'])
@jwt_required()
def listar_pendientes():
    """
    Listar items pendientes de entrega.

    Query params:
      - estado (str, default='PENDIENTE'): PENDIENTE, ENTREGADO, CANCELADO
      - colegio_id (int, opcional): filtrar por colegio
      - factura_id (int, opcional): filtrar por factura
      - tipo (str, opcional): 'stock' o 'prenda' o ambos
      - page (int, default=1)
      - per_page (int, default=20, max=100)

    Response:
      {
        "pendientes": [
          {
            "id_pendiente": 1,
            "id_factura": 5,
            "numero_factura": "FAC-2026-000001",
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "producto_nombre": "Uniforme Niño",
            "talla": "8",
            "cantidad_faltante": 2,
            "estado": "PENDIENTE",
            "fecha_registro": "2026-02-28"
          },
          ...
        ],
        "total": 45,
        "pages": 3,
        "page": 1,
        "resumen": {
          "pendientes": 30,
          "entregados": 15,
          "cancelados": 0
        }
      }
    """
    estado = request.args.get('estado', 'PENDIENTE')
    colegio_id = request.args.get('colegio_id', type=int)
    factura_id = request.args.get('factura_id', type=int)
    tipo = request.args.get('tipo', 'stock').lower()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = StockPendiente.query

    if estado:
        query = query.filter(StockPendiente.estado == estado)
    if colegio_id:
        query = query.filter(StockPendiente.id_colegio == colegio_id)
    if factura_id:
        query = query.filter(StockPendiente.id_factura == factura_id)

    query = query.order_by(StockPendiente.fecha_registro.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    # Contar resumen de estados
    resumen_query = StockPendiente.query
    if colegio_id:
        resumen_query = resumen_query.filter(StockPendiente.id_colegio == colegio_id)
    if factura_id:
        resumen_query = resumen_query.filter(StockPendiente.id_factura == factura_id)

    resumen = {
        'pendientes': resumen_query.filter(StockPendiente.estado == 'PENDIENTE').count(),
        'entregados': resumen_query.filter(StockPendiente.estado == 'ENTREGADO').count(),
        'cancelados': resumen_query.filter(StockPendiente.estado == 'CANCELADO').count(),
    }

    return jsonify({
        'pendientes': [p.to_dict() for p in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page': page,
        'resumen': resumen,
    }), 200


@pendientes_bp.route('/por-colegio', methods=['GET'])
@jwt_required()
def listar_pendientes_por_colegio():
    """
    Listar pendientes agrupados por colegio (útil para costureras).

    Query params:
      - estado (str, default='PENDIENTE'): PENDIENTE, ENTREGADO, CANCELADO
      - ordenar (str, default='colegio'): 'colegio' o 'fecha'

    Response:
      {
        "pendientes_por_colegio": [
          {
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "total": 10,
            "items": [
              {
                "id_pendiente": 1,
                "numero_factura": "FAC-2026-000001",
                "producto_nombre": "Uniforme Niño",
                "talla": "8",
                "cantidad_faltante": 2,
                "estado": "PENDIENTE",
                "fecha_registro": "2026-02-28"
              },
              ...
            ]
          },
          ...
        ],
        "total_items": 45,
        "total_colegios": 8
      }
    """
    estado = request.args.get('estado', 'PENDIENTE')
    ordenar = request.args.get('ordenar', 'colegio').lower()

    query = StockPendiente.query
    if estado:
        query = query.filter(StockPendiente.estado == estado)

    pendientes = query.order_by(
        StockPendiente.id_colegio,
        StockPendiente.fecha_registro.desc()
    ).all()

    # Agrupar por colegio
    por_colegio = {}
    for p in pendientes:
        colegio_id = p.id_colegio
        if colegio_id not in por_colegio:
            por_colegio[colegio_id] = {
                'id_colegio': colegio_id,
                'colegio_nombre': p.colegio.nombre if p.colegio else f'Colegio {colegio_id}',
                'items': [],
            }
        por_colegio[colegio_id]['items'].append({
            'id_pendiente': p.id_pendiente,
            'id_factura': p.id_factura,
            'numero_factura': p.factura.numero_factura if p.factura else None,
            'producto_nombre': p.producto.nombre if p.producto else None,
            'talla': p.talla_individual,
            'cantidad_faltante': p.cantidad_faltante,
            'estado': p.estado,
            'fecha_registro': p.fecha_registro.isoformat() if p.fecha_registro else None,
        })

    resultado = list(por_colegio.values())
    for grupo in resultado:
        grupo['total'] = len(grupo['items'])

    if ordenar == 'fecha':
        resultado = sorted(resultado, key=lambda x: x['items'][0]['fecha_registro'] if x['items'] else '', reverse=True)

    return jsonify({
        'pendientes_por_colegio': resultado,
        'total_items': len(pendientes),
        'total_colegios': len(por_colegio),
    }), 200


@pendientes_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_pendientes():
    """
    Obtener conteo resumido de pendientes por estado.

    Response:
      {
        "resumen": {
          "total_pendientes": 30,
          "total_entregados": 45,
          "total_cancelados": 2
        },
        "por_colegio": [
          {
            "id_colegio": 3,
            "colegio_nombre": "Colegio A",
            "pendientes": 5,
            "entregados": 10,
            "cancelados": 0
          },
          ...
        ]
      }
    """
    # Resumen general
    resumen = {
        'total_pendientes': StockPendiente.query.filter(StockPendiente.estado == 'PENDIENTE').count(),
        'total_entregados': StockPendiente.query.filter(StockPendiente.estado == 'ENTREGADO').count(),
        'total_cancelados': StockPendiente.query.filter(StockPendiente.estado == 'CANCELADO').count(),
    }

    # Por colegio
    por_colegio_data = db.session.query(
        StockPendiente.id_colegio,
        func.sum(db.case((StockPendiente.estado == 'PENDIENTE', 1), else_=0)).label('pendientes'),
        func.sum(db.case((StockPendiente.estado == 'ENTREGADO', 1), else_=0)).label('entregados'),
        func.sum(db.case((StockPendiente.estado == 'CANCELADO', 1), else_=0)).label('cancelados'),
    ).group_by(StockPendiente.id_colegio).all()

    por_colegio = []
    for row in por_colegio_data:
        colegio = db.session.query(db.func.name).filter(
            db.Model.metadata.tables['colegios'].c.id_colegio == row.id_colegio
        ).scalar()
        por_colegio.append({
            'id_colegio': row.id_colegio,
            'pendientes': row.pendientes or 0,
            'entregados': row.entregados or 0,
            'cancelados': row.cancelados or 0,
        })

    return jsonify({
        'resumen': resumen,
        'por_colegio': por_colegio,
    }), 200


@pendientes_bp.route('/<int:id_pendiente>/entregar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def entregar_pendiente(id_pendiente):
    """
    Marcar un pendiente como entregado.

    Body JSON (opcional):
      {
        "observaciones": "Se entregó en persona"
      }
    """
    pendiente = StockPendiente.query.get_or_404(id_pendiente)
    identity = get_current_identity()

    if pendiente.estado != 'PENDIENTE':
        return jsonify({'error': 'Este pendiente ya fue procesado'}), 400

    pendiente.estado = 'ENTREGADO'
    data = request.get_json() or {}
    observaciones = data.get('observaciones', '')

    db.session.commit()

    registrar_auditoria(
        'stock_pendiente',
        id_pendiente,
        'ENTREGAR',
        f'Pendiente entregado por {identity["usuario"]}. {observaciones}' if observaciones else f'Pendiente entregado por {identity["usuario"]}'
    )

    return jsonify({
        'message': 'Pendiente marcado como entregado',
        'pendiente': pendiente.to_dict()
    }), 200


@pendientes_bp.route('/entregar-lote', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def entregar_lote():
    """
    Marcar múltiples pendientes como entregados.

    Body JSON:
      {
        "ids": [1, 2, 3, ...],
        "observaciones": "Entrega a granel" (opcional)
      }

    Returns:
      {
        "message": "3 pendientes marcados como entregados",
        "entregas_exitosas": 3,
        "entregas_fallidas": 0,
        "errores": []
      }
    """
    data = request.get_json()
    identity = get_current_identity()

    ok, msg = validate_required_fields(data, ['ids'])
    if not ok:
        return jsonify({'error': msg}), 400

    ids = data.get('ids', [])
    if not isinstance(ids, list) or len(ids) == 0:
        return jsonify({'error': 'ids debe ser una lista no vacía'}), 400

    observaciones = data.get('observaciones', '')
    entregas_exitosas = 0
    entregas_fallidas = 0
    errores = []

    for id_pendiente in ids:
        try:
            pendiente = StockPendiente.query.get(id_pendiente)
            if not pendiente:
                errores.append({
                    'id_pendiente': id_pendiente,
                    'error': 'Pendiente no encontrado'
                })
                entregas_fallidas += 1
                continue

            if pendiente.estado != 'PENDIENTE':
                errores.append({
                    'id_pendiente': id_pendiente,
                    'error': f'Pendiente ya fue procesado (estado: {pendiente.estado})'
                })
                entregas_fallidas += 1
                continue

            pendiente.estado = 'ENTREGADO'
            entregas_exitosas += 1

            registrar_auditoria(
                'stock_pendiente',
                id_pendiente,
                'ENTREGAR',
                f'Entrega en lote por {identity["usuario"]}. {observaciones}' if observaciones else f'Entrega en lote por {identity["usuario"]}'
            )

        except Exception as e:
            errores.append({
                'id_pendiente': id_pendiente,
                'error': str(e)
            })
            entregas_fallidas += 1

    db.session.commit()

    return jsonify({
        'message': f'{entregas_exitosas} pendientes marcados como entregados',
        'entregas_exitosas': entregas_exitosas,
        'entregas_fallidas': entregas_fallidas,
        'errores': errores,
    }), 200
