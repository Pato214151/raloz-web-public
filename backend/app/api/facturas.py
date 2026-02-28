"""
API de Facturación
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, FacturaDetalle, Stock, SerieFacturacion, StockPendiente
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import sanitize_string, validate_date, validate_positive_number, validate_required_fields
from datetime import datetime, date

facturas_bp = Blueprint('facturas', __name__)


@facturas_bp.route('', methods=['GET'])
@jwt_required()
def listar_facturas():
    """Listar facturas con filtros y paginación"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    estado = request.args.get('estado')
    colegio_id = request.args.get('colegio_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    buscar = request.args.get('buscar', '').strip()

    query = Factura.query

    if estado:
        query = query.filter(Factura.estado == estado)
    if colegio_id:
        query = query.filter(Factura.id_colegio == colegio_id)
    if fecha_desde:
        fd = validate_date(fecha_desde)
        if fd:
            query = query.filter(Factura.fecha_factura >= fd)
    if fecha_hasta:
        fh = validate_date(fecha_hasta)
        if fh:
            query = query.filter(Factura.fecha_factura <= fh)
    if buscar:
        buscar_like = f'%{buscar}%'
        query = query.filter(
            (Factura.numero_factura.ilike(buscar_like)) |
            (Factura.cliente_nombre.ilike(buscar_like)) |
            (Factura.cliente_telefono.ilike(buscar_like))
        )

    query = query.order_by(Factura.fecha_creacion.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'facturas': [f.to_dict() for f in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page': page,
    }), 200


@facturas_bp.route('/<int:id_factura>', methods=['GET'])
@jwt_required()
def obtener_factura(id_factura):
    """Obtener factura con detalles y pagos"""
    factura = Factura.query.get_or_404(id_factura)
    return jsonify({'factura': factura.to_dict_full()}), 200


@facturas_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
def crear_factura():
    """Crear nueva factura"""
    data = request.get_json()
    identity = get_current_identity()

    # Validar campos requeridos
    ok, msg = validate_required_fields(data, ['id_colegio', 'cliente_nombre', 'detalles'])
    if not ok:
        return jsonify({'error': msg}), 400

    if not data.get('detalles') or len(data['detalles']) == 0:
        return jsonify({'error': 'La factura debe tener al menos un producto'}), 400

    try:
        # Generar número de factura
        serie = SerieFacturacion.query.filter_by(activa=True).first()
        if not serie:
            ano_actual = datetime.now().year
            serie = SerieFacturacion(ano=ano_actual, consecutivo_actual=0)
            db.session.add(serie)

        serie.consecutivo_actual += 1
        numero = f"FAC-{serie.ano}-{serie.consecutivo_actual:06d}"

        # Calcular total
        total = 0
        detalles_validados = []

        for item in data['detalles']:
            cantidad = int(item.get('cantidad', 0))
            precio = float(item.get('precio_unitario', 0))
            if cantidad <= 0 or precio <= 0:
                return jsonify({'error': 'Cantidad y precio deben ser positivos'}), 400

            total_linea = cantidad * precio
            total += total_linea

            detalles_validados.append({
                'id_producto': int(item['id_producto']),
                'talla_individual': sanitize_string(item.get('talla_individual', ''), 20),
                'cantidad': cantidad,
                'precio_unitario': precio,
                'total_linea': total_linea,
            })

        fecha_factura = validate_date(data.get('fecha_factura', '')) or date.today()

        # Crear factura
        factura = Factura(
            numero_factura=numero,
            id_colegio=int(data['id_colegio']),
            cliente_nombre=sanitize_string(data['cliente_nombre'], 200),
            cliente_telefono=sanitize_string(data.get('cliente_telefono', ''), 50),
            fecha_factura=fecha_factura,
            total=total,
            estado='PENDIENTE',
            usuario_creacion=identity['usuario'],
        )
        db.session.add(factura)
        db.session.flush()  # Para obtener el id_factura

        # Crear detalles y descontar stock
        for det in detalles_validados:
            detalle = FacturaDetalle(
                id_factura=factura.id_factura,
                **det
            )
            db.session.add(detalle)

            # Descontar stock
            stock = Stock.query.filter_by(
                id_colegio=int(data['id_colegio']),
                id_producto=det['id_producto'],
                talla_individual=det['talla_individual']
            ).first()

            if stock:
                disponible = stock.cantidad
                if disponible >= det['cantidad']:
                    stock.cantidad -= det['cantidad']
                else:
                    # Stock parcial - crear pendiente
                    stock.cantidad = 0
                    faltante = det['cantidad'] - disponible
                    pendiente = StockPendiente(
                        id_factura=factura.id_factura,
                        id_colegio=int(data['id_colegio']),
                        id_producto=det['id_producto'],
                        talla_individual=det['talla_individual'],
                        cantidad_faltante=faltante,
                    )
                    db.session.add(pendiente)
            else:
                # No hay stock - todo pendiente
                pendiente = StockPendiente(
                    id_factura=factura.id_factura,
                    id_colegio=int(data['id_colegio']),
                    id_producto=det['id_producto'],
                    talla_individual=det['talla_individual'],
                    cantidad_faltante=det['cantidad'],
                )
                db.session.add(pendiente)

        # Registrar abono inicial si existe
        abono = float(data.get('abono', 0))
        if abono > 0:
            from app.models import Pago
            pago = Pago(
                id_factura=factura.id_factura,
                fecha_pago=fecha_factura,
                valor=min(abono, total),
                metodo_pago=sanitize_string(data.get('metodo_pago', 'EFECTIVO'), 50),
                usuario_registro=identity['usuario'],
            )
            db.session.add(pago)
            if abono >= total:
                factura.estado = 'PAGADA'

        db.session.commit()
        registrar_auditoria('facturas', factura.id_factura, 'CREAR', f'Factura {numero}')

        return jsonify({
            'message': 'Factura creada exitosamente',
            'factura': factura.to_dict_full()
        }), 201

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Error en datos: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear factura'}), 500


@facturas_bp.route('/<int:id_factura>/anular', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def anular_factura(id_factura):
    """Anular factura (solo admin)"""
    factura = Factura.query.get_or_404(id_factura)

    if factura.estado == 'ANULADA':
        return jsonify({'error': 'Factura ya está anulada'}), 400

    factura.estado = 'ANULADA'

    # Devolver stock
    for detalle in factura.detalles:
        stock = Stock.query.filter_by(
            id_colegio=factura.id_colegio,
            id_producto=detalle.id_producto,
            talla_individual=detalle.talla_individual,
        ).first()
        if stock:
            stock.cantidad += detalle.cantidad

    db.session.commit()
    registrar_auditoria('facturas', id_factura, 'ANULAR', f'Factura {factura.numero_factura}')

    return jsonify({'message': 'Factura anulada', 'factura': factura.to_dict()}), 200
