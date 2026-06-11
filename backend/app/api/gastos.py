"""
API de Gastos
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Gasto
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import sanitize_string, validate_date
from datetime import date

gastos_bp = Blueprint('gastos', __name__)


@gastos_bp.route('', methods=['GET'])
@jwt_required()
def listar_gastos():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 500)
    fecha = request.args.get('fecha')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    categoria = request.args.get('categoria')
    metodo_pago = request.args.get('metodo_pago')
    tipo_gasto = request.args.get('tipo_gasto')
    estado_pago = request.args.get('estado_pago')  # 'PAGADO' | 'PENDIENTE' (deudas)

    query = Gasto.query

    if estado_pago:
        query = query.filter(Gasto.estado_pago == estado_pago)
    if fecha:
        fd = validate_date(fecha)
        if fd:
            query = query.filter(Gasto.fecha == fd)
    if categoria:
        query = query.filter(Gasto.categoria == categoria)
    if metodo_pago:
        query = query.filter(Gasto.metodo_pago == metodo_pago)
    if tipo_gasto:
        query = query.filter(Gasto.tipo_gasto == tipo_gasto)
    if fecha_desde:
        fd = validate_date(fecha_desde)
        if fd:
            query = query.filter(Gasto.fecha >= fd)
    if fecha_hasta:
        fh = validate_date(fecha_hasta)
        if fh:
            query = query.filter(Gasto.fecha <= fh)

    query = query.order_by(Gasto.fecha.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'gastos': [g.to_dict() for g in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
    }), 200


@gastos_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def crear_gasto():
    data = request.get_json()
    identity = get_current_identity()

    descripcion = sanitize_string(data.get('descripcion', ''), 500)
    if not descripcion:
        return jsonify({'error': 'Descripción requerida'}), 400

    try:
        valor = float(data.get('valor', 0))
        if valor <= 0:
            return jsonify({'error': 'Valor debe ser positivo'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Valor inválido'}), 400

    fecha = validate_date(data.get('fecha', '')) or date.today()

    tipo_gasto = sanitize_string(data.get('tipo_gasto', 'TIENDA'), 20)
    if tipo_gasto not in ('TIENDA', 'EMPRESA'):
        tipo_gasto = 'TIENDA'

    # Si es una deuda (debo ahora, pago después), no cuenta como gasto hasta pagarla.
    es_deuda = bool(data.get('es_deuda'))

    gasto = Gasto(
        fecha=fecha,
        descripcion=descripcion,
        valor=valor,
        metodo_pago=sanitize_string(data.get('metodo_pago', 'EFECTIVO'), 50),
        categoria=sanitize_string(data.get('categoria', 'Otros'), 100),
        tipo_gasto=tipo_gasto,
        estado_pago='PENDIENTE' if es_deuda else 'PAGADO',
        usuario_registro=identity['usuario'],
    )
    db.session.add(gasto)
    db.session.commit()
    accion = 'CREAR_DEUDA' if es_deuda else 'CREAR'
    registrar_auditoria('gastos', gasto.id_gasto, accion, f'{"Deuda" if es_deuda else "Gasto"}: {descripcion} ${valor:,.0f}')

    return jsonify({'message': 'Deuda registrada' if es_deuda else 'Gasto registrado', 'gasto': gasto.to_dict()}), 201


@gastos_bp.route('/<int:id_gasto>/pagar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def pagar_deuda(id_gasto):
    """Marca una deuda pendiente como pagada. Ahí se convierte en gasto real,
    fechado el día del pago (cuenta en el balance de ese mes)."""
    gasto = Gasto.query.get_or_404(id_gasto)
    if (gasto.estado_pago or 'PAGADO') != 'PENDIENTE':
        return jsonify({'error': 'Este gasto no es una deuda pendiente'}), 400

    data = request.get_json() or {}
    hoy = date.today()
    gasto.estado_pago = 'PAGADO'
    gasto.fecha_pago = hoy
    gasto.fecha = hoy  # cuenta como gasto del día en que se paga
    metodo = sanitize_string(data.get('metodo_pago', ''), 50)
    if metodo:
        gasto.metodo_pago = metodo
    db.session.commit()
    registrar_auditoria('gastos', id_gasto, 'PAGAR_DEUDA',
                        f'Deuda pagada: {gasto.descripcion} ${gasto.valor:,.0f}')
    return jsonify({'message': 'Deuda marcada como pagada', 'gasto': gasto.to_dict()}), 200


@gastos_bp.route('/<int:id_gasto>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador', 'cajero')
def editar_gasto(id_gasto):
    """Editar un gasto existente"""
    gasto = Gasto.query.get_or_404(id_gasto)
    data = request.get_json()

    if 'descripcion' in data:
        gasto.descripcion = sanitize_string(data['descripcion'], 500)
    if 'valor' in data:
        try:
            valor = float(data['valor'])
            if valor <= 0:
                return jsonify({'error': 'Valor debe ser positivo'}), 400
            gasto.valor = valor
        except (ValueError, TypeError):
            return jsonify({'error': 'Valor inválido'}), 400
    if 'metodo_pago' in data:
        gasto.metodo_pago = sanitize_string(data['metodo_pago'], 50)
    if 'categoria' in data:
        gasto.categoria = sanitize_string(data['categoria'], 100)
    if 'tipo_gasto' in data:
        tg = sanitize_string(data['tipo_gasto'], 20)
        if tg in ('TIENDA', 'EMPRESA'):
            gasto.tipo_gasto = tg
    if 'fecha' in data:
        nueva_fecha = validate_date(data['fecha'])
        if nueva_fecha:
            gasto.fecha = nueva_fecha

    db.session.commit()
    registrar_auditoria('gastos', id_gasto, 'EDITAR', f'Gasto editado: {gasto.descripcion}')

    return jsonify({'message': 'Gasto actualizado', 'gasto': gasto.to_dict()}), 200


@gastos_bp.route('/<int:id_gasto>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_gasto(id_gasto):
    """Eliminar un gasto"""
    gasto = Gasto.query.get_or_404(id_gasto)
    info = f'Gasto eliminado: {gasto.descripcion} ${gasto.valor:,.0f}'

    db.session.delete(gasto)
    db.session.commit()
    registrar_auditoria('gastos', id_gasto, 'ELIMINAR', info)

    return jsonify({'message': 'Gasto eliminado'}), 200
