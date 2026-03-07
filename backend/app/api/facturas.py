"""
API de Facturación
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, FacturaDetalle, Stock, SerieFacturacion, StockPendiente, Pago, PrendaPendiente, Producto
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

    # Calcular saldo total de los resultados filtrados
    saldo_total_query = query.order_by(None).with_entities(db.func.sum(Factura.saldo_pendiente)).scalar() or 0

    return jsonify({
        'facturas': [f.to_dict() for f in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page': page,
        'saldo_total': float(saldo_total_query),
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
    """Crear nueva factura con todos los campos"""
    data = request.get_json()
    identity = get_current_identity()

    ok, msg = validate_required_fields(data, ['id_colegio', 'cliente_nombre', 'detalles'])
    if not ok:
        return jsonify({'error': msg}), 400

    if not data.get('detalles') or len(data['detalles']) == 0:
        return jsonify({'error': 'La factura debe tener al menos un producto'}), 400

    try:
        # Generar número de factura
        numero_custom = sanitize_string(data.get('numero_factura', ''), 50).strip()
        if numero_custom:
            if Factura.query.filter_by(numero_factura=numero_custom).first():
                return jsonify({'error': f'Ya existe una factura con el número {numero_custom}'}), 409
            numero = numero_custom
        else:
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
        abono = float(data.get('abono', 0))
        domicilio = float(data.get('domicilio', 0))
        total_con_domicilio = total + domicilio

        # Crear factura con todos los campos
        factura = Factura(
            numero_factura=numero,
            id_colegio=int(data['id_colegio']),
            cliente_nombre=sanitize_string(data['cliente_nombre'], 200),
            cliente_telefono=sanitize_string(data.get('cliente_telefono', ''), 50),
            cliente_email=sanitize_string(data.get('cliente_email', ''), 255),
            cliente_direccion=sanitize_string(data.get('cliente_direccion', ''), 500),
            cliente_nit=sanitize_string(data.get('cliente_nit', ''), 50),
            genero_estudiante=sanitize_string(data.get('genero_estudiante', ''), 20),
            fecha_factura=fecha_factura,
            total=total_con_domicilio,
            subtotal=total,
            domicilio=domicilio,
            total_abonado=min(abono, total_con_domicilio) if abono > 0 else 0,
            saldo_pendiente=max(total_con_domicilio - abono, 0) if abono > 0 else total_con_domicilio,
            estado='PAGADA' if abono >= total_con_domicilio and abono > 0 else 'PENDIENTE',
            estado_entrega='ENTREGADA' if data.get('entrega_inmediata') else 'POR_ENTREGAR',
            metodo_pago=sanitize_string(data.get('metodo_pago', 'EFECTIVO'), 50),
            observaciones=sanitize_string(data.get('observaciones', ''), 1000),
            usuario_creacion=identity['usuario'],
        )
        db.session.add(factura)
        db.session.flush()

        entrega_inmediata = bool(data.get('entrega_inmediata', False))
        id_colegio = int(data['id_colegio'])
        colegio = factura.colegio

        # Crear detalles
        for det in detalles_validados:
            detalle = FacturaDetalle(id_factura=factura.id_factura, **det)
            db.session.add(detalle)

            if entrega_inmediata:
                # Descontar del inventario
                stock = Stock.query.filter_by(
                    id_colegio=id_colegio,
                    id_producto=det['id_producto'],
                    talla_individual=det['talla_individual']
                ).first()
                if stock:
                    stock.cantidad = max(0, stock.cantidad - det['cantidad'])
            else:
                # Guardar como prenda pendiente de entrega
                producto = Producto.query.get(det['id_producto'])
                prenda = PrendaPendiente(
                    id_factura=factura.id_factura,
                    numero_factura=numero,
                    id_colegio=id_colegio,
                    colegio_nombre=colegio.nombre if colegio else None,
                    cliente_nombre=factura.cliente_nombre,
                    producto_nombre=producto.nombre if producto else f'Producto {det["id_producto"]}',
                    talla=det['talla_individual'],
                    cantidad=det['cantidad'],
                    genero=sanitize_string(data.get('genero_estudiante', 'NIÑO'), 20) or 'NIÑO',
                    estado='PENDIENTE',
                    fecha_registro=date.today(),
                    fecha_factura=fecha_factura,
                    usuario_registro=identity['usuario'],
                )
                db.session.add(prenda)

        # Registrar abono inicial
        if abono > 0:
            pago = Pago(
                id_factura=factura.id_factura,
                fecha_pago=fecha_factura,
                valor=min(abono, total),
                metodo_pago=sanitize_string(data.get('metodo_pago', 'EFECTIVO'), 50),
                usuario_registro=identity['usuario'],
            )
            db.session.add(pago)

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


@facturas_bp.route('/<int:id_factura>', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def editar_factura(id_factura):
    """Editar factura existente: datos del cliente y/o productos"""
    factura = Factura.query.get_or_404(id_factura)
    identity = get_current_identity()

    if factura.estado == 'ANULADA':
        return jsonify({'error': 'No se puede editar una factura anulada'}), 400

    data = request.get_json()

    try:
        # Actualizar datos del cliente si se envían
        campos_cliente = ['cliente_nombre', 'cliente_telefono', 'cliente_email',
                          'cliente_direccion', 'cliente_nit', 'genero_estudiante',
                          'metodo_pago', 'estado_entrega', 'observaciones']
        for campo in campos_cliente:
            if campo in data:
                setattr(factura, campo, sanitize_string(data[campo], 500))

        if 'fecha_factura' in data:
            nueva_fecha = validate_date(data['fecha_factura'])
            if nueva_fecha:
                factura.fecha_factura = nueva_fecha

        # Si se envían nuevos detalles, reemplazar productos
        if 'detalles' in data and isinstance(data['detalles'], list) and len(data['detalles']) > 0:
            # Devolver stock de detalles actuales
            for det_old in factura.detalles:
                stock = Stock.query.filter_by(
                    id_colegio=factura.id_colegio,
                    id_producto=det_old.id_producto,
                    talla_individual=det_old.talla_individual,
                ).first()
                if stock:
                    stock.cantidad += det_old.cantidad

            # Eliminar detalles anteriores
            FacturaDetalle.query.filter_by(id_factura=id_factura).delete()

            # Eliminar stock pendiente anterior
            StockPendiente.query.filter_by(id_factura=id_factura).delete()

            # Crear nuevos detalles
            nuevo_total = 0
            for item in data['detalles']:
                cantidad = int(item.get('cantidad', 0))
                precio = float(item.get('precio_unitario', 0))
                if cantidad <= 0 or precio <= 0:
                    return jsonify({'error': 'Cantidad y precio deben ser positivos'}), 400

                total_linea = cantidad * precio
                nuevo_total += total_linea

                detalle = FacturaDetalle(
                    id_factura=id_factura,
                    id_producto=int(item['id_producto']),
                    talla_individual=sanitize_string(item.get('talla_individual', ''), 20),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    total_linea=total_linea,
                )
                db.session.add(detalle)

                # Descontar nuevo stock
                stock = Stock.query.filter_by(
                    id_colegio=factura.id_colegio,
                    id_producto=int(item['id_producto']),
                    talla_individual=sanitize_string(item.get('talla_individual', ''), 20),
                ).first()

                if stock:
                    if stock.cantidad >= cantidad:
                        stock.cantidad -= cantidad
                    else:
                        faltante = cantidad - stock.cantidad
                        stock.cantidad = 0
                        db.session.add(StockPendiente(
                            id_factura=id_factura,
                            id_colegio=factura.id_colegio,
                            id_producto=int(item['id_producto']),
                            talla_individual=sanitize_string(item.get('talla_individual', ''), 20),
                            cantidad_faltante=faltante,
                        ))
                else:
                    db.session.add(StockPendiente(
                        id_factura=id_factura,
                        id_colegio=factura.id_colegio,
                        id_producto=int(item['id_producto']),
                        talla_individual=sanitize_string(item.get('talla_individual', ''), 20),
                        cantidad_faltante=cantidad,
                    ))

            factura.total = nuevo_total
            factura.subtotal = nuevo_total

            # Recalcular saldo
            total_pagado = sum(p.valor for p in factura.pagos)
            factura.total_abonado = total_pagado
            factura.saldo_pendiente = max(nuevo_total - total_pagado, 0)
            if total_pagado >= nuevo_total:
                factura.estado = 'PAGADA'
            elif total_pagado > 0:
                factura.estado = 'PENDIENTE'

        db.session.commit()
        registrar_auditoria('facturas', id_factura, 'EDITAR', f'Factura {factura.numero_factura} editada por {identity["usuario"]}')

        return jsonify({
            'message': 'Factura actualizada',
            'factura': factura.to_dict_full()
        }), 200

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'error': f'Error en datos: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al editar factura'}), 500


@facturas_bp.route('/<int:id_factura>/anular', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def anular_factura(id_factura):
    """Anular factura (solo admin)"""
    factura = Factura.query.get_or_404(id_factura)
    identity = get_current_identity()

    if factura.estado == 'ANULADA':
        return jsonify({'error': 'Factura ya está anulada'}), 400

    factura.estado = 'ANULADA'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    nota = f"[ANULADA por {identity['usuario']} el {timestamp}]"
    factura.observaciones = f"{factura.observaciones or ''} {nota}".strip()

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


@facturas_bp.route('/<int:id_factura>/reactivar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def reactivar_factura(id_factura):
    """Reactivar factura anulada (solo admin)"""
    factura = Factura.query.get_or_404(id_factura)
    identity = get_current_identity()

    if factura.estado != 'ANULADA':
        return jsonify({'error': 'Solo se pueden reactivar facturas anuladas'}), 400

    # Recalcular estado basado en pagos
    total_pagado = sum(p.valor for p in factura.pagos)
    if total_pagado >= factura.total:
        factura.estado = 'PAGADA'
    else:
        factura.estado = 'PENDIENTE'

    factura.total_abonado = total_pagado
    factura.saldo_pendiente = max(factura.total - total_pagado, 0)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    nota = f"[REACTIVADA por {identity['usuario']} el {timestamp}]"
    factura.observaciones = f"{factura.observaciones or ''} {nota}".strip()

    db.session.commit()
    registrar_auditoria('facturas', id_factura, 'REACTIVAR', f'Factura {factura.numero_factura}')

    return jsonify({
        'message': 'Factura reactivada',
        'factura': factura.to_dict(),
        'resumen': {
            'estado': factura.estado,
            'total_pagado': total_pagado,
            'saldo_pendiente': factura.saldo_pendiente,
        }
    }), 200
