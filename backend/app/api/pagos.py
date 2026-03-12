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


def _recalcular_factura(factura):
    """Recalcular totales de factura después de modificar pagos"""
    total_pagado = sum(p.valor for p in factura.pagos)
    factura.total_abonado = total_pagado
    factura.saldo_pendiente = max(factura.total - total_pagado, 0)

    if factura.estado == 'ANULADA':
        return

    if total_pagado >= factura.total:
        factura.estado = 'PAGADA'
    elif total_pagado > 0:
        factura.estado = 'PENDIENTE'
    else:
        factura.estado = 'PENDIENTE'


@pagos_bp.route('', methods=['GET'])
@jwt_required()
def listar_pagos():
    """Listar pagos con filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    metodo = request.args.get('metodo_pago')
    id_factura = request.args.get('id_factura', type=int)

    query = Pago.query

    if id_factura:
        query = query.filter(Pago.id_factura == id_factura)
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

    nuevo_saldo = saldo - valor
    if nuevo_saldo <= 0:
        factura.estado = 'PAGADA'

    factura.total_abonado = total_pagado + valor
    factura.saldo_pendiente = max(nuevo_saldo, 0)

    db.session.commit()
    registrar_auditoria('pagos', pago.id_pago, 'CREAR', f'Pago ${valor:,.0f} a factura {factura.numero_factura}')

    return jsonify({
        'message': 'Pago registrado',
        'pago': pago.to_dict(),
        'factura': factura.to_dict(),
        'saldo_restante': nuevo_saldo,
    }), 201


@pagos_bp.route('/<int:id_pago>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def editar_pago(id_pago):
    """Editar un pago existente (solo admin)"""
    pago = Pago.query.get_or_404(id_pago)
    data = request.get_json()
    identity = get_current_identity()

    factura = Factura.query.get_or_404(pago.id_factura)

    try:
        if 'valor' in data:
            nuevo_valor = float(data['valor'])
            if nuevo_valor <= 0:
                return jsonify({'error': 'El valor debe ser positivo'}), 400

            # Verificar que no exceda el total
            total_otros_pagos = sum(p.valor for p in factura.pagos if p.id_pago != id_pago)
            saldo_disponible = factura.total - total_otros_pagos
            if nuevo_valor > saldo_disponible:
                return jsonify({
                    'error': f'El valor (${nuevo_valor:,.0f}) excede el saldo disponible (${saldo_disponible:,.0f})'
                }), 400

            valor_anterior = pago.valor
            pago.valor = nuevo_valor

        if 'metodo_pago' in data:
            pago.metodo_pago = sanitize_string(data['metodo_pago'], 50)

        if 'fecha_pago' in data:
            nueva_fecha = validate_date(data['fecha_pago'])
            if nueva_fecha:
                pago.fecha_pago = nueva_fecha

        _recalcular_factura(factura)

        db.session.commit()
        registrar_auditoria('pagos', id_pago, 'EDITAR', f'Pago editado por {identity["usuario"]}')

        return jsonify({
            'message': 'Pago actualizado',
            'pago': pago.to_dict(),
            'factura': factura.to_dict(),
        }), 200

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Error en datos: {str(e)}'}), 400


@pagos_bp.route('/<int:id_pago>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_pago(id_pago):
    """Eliminar un pago (solo admin)"""
    pago = Pago.query.get_or_404(id_pago)
    identity = get_current_identity()

    factura = Factura.query.get_or_404(pago.id_factura)

    info = f'Pago ${pago.valor:,.0f} de factura {factura.numero_factura} eliminado por {identity["usuario"]}'

    db.session.delete(pago)
    _recalcular_factura(factura)
    db.session.commit()

    registrar_auditoria('pagos', id_pago, 'ELIMINAR', info)

    return jsonify({
        'message': 'Pago eliminado',
        'factura': factura.to_dict(),
    }), 200
