"""
API de Pagos
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, Pago
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import sanitize_string, validate_date
from datetime import date

pagos_bp = Blueprint('pagos', __name__)


@pagos_bp.route('', methods=['GET'])
@jwt_required()
def listar_pagos():
    """Listar pagos con filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    metodo = request.args.get('metodo_pago')

    query = Pago.query

    if fecha_desde:
        fd = validate_date(fecha_desde)
        if fd:
            query = query.filter(Pago.fecha_pago >= fd)
    if fecha_hasta:
        fh = validate_date(fecha_hasta)
        if fh:
            query = query.filter(Pago.fecha_pago <= fh)
    if metodo:
        query = query.filter(Pago.metodo_pago == metodo)

    query = query.order_by(Pago.fecha_registro.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'pagos': [p.to_dict() for p in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page': page,
    }), 200


@pagos_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def registrar_pago():
    """Registrar pago a una factura"""
    data = request.get_json()
    identity = get_current_identity()

    id_factura = data.get('id_factura')
    valor = data.get('valor')
    metodo_pago = sanitize_string(data.get('metodo_pago', 'EFECTIVO'), 50)

    if not id_factura or not valor:
        return jsonify({'error': 'Factura y valor requeridos'}), 400

    try:
        valor = float(valor)
        if valor <= 0:
            return jsonify({'error': 'El valor debe ser positivo'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Valor inválido'}), 400

    factura = Factura.query.get_or_404(id_factura)

    if factura.estado == 'ANULADA':
        return jsonify({'error': 'No se puede pagar una factura anulada'}), 400

    # Calcular saldo
    total_pagado = sum(p.valor for p in factura.pagos)
    saldo = factura.total - total_pagado

    if valor > saldo:
        return jsonify({
            'error': f'El pago (${valor:,.0f}) excede el saldo (${saldo:,.0f})',
            'saldo': saldo,
        }), 400

    fecha_pago = validate_date(data.get('fecha_pago', '')) or date.today()

    pago = Pago(
        id_factura=id_factura,
        fecha_pago=fecha_pago,
        valor=valor,
        metodo_pago=metodo_pago,
        usuario_registro=identity['usuario'],
    )
    db.session.add(pago)

    # Actualizar estado
    nuevo_saldo = saldo - valor
    if nuevo_saldo <= 0:
        factura.estado = 'PAGADA'
    else:
        factura.estado = 'ABONO'

    db.session.commit()
    registrar_auditoria('pagos', pago.id_pago, 'CREAR', f'Pago ${valor:,.0f} a factura {factura.numero_factura}')

    return jsonify({
        'message': 'Pago registrado',
        'pago': pago.to_dict(),
        'factura': factura.to_dict(),
        'saldo_restante': nuevo_saldo,
    }), 201
