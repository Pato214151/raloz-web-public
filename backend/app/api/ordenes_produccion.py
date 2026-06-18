"""
API de Órdenes de Producción (confección al taller). Solo administrador.
Crear, listar, ver, imprimir PDF y cambiar estado / eliminar.
"""
import json

from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func

from app import db
from app.models import OrdenProduccion, Colegio
from app.utils.decorators import admin_requerido, get_current_identity, registrar_auditoria
from app.services.orden_produccion_pdf import generar_pdf_orden

ordenes_produccion_bp = Blueprint('ordenes_produccion', __name__)


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@ordenes_produccion_bp.route('', methods=['GET'])
@admin_requerido
def listar():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 200)
    q = request.args.get('q', '').strip()

    query = OrdenProduccion.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            OrdenProduccion.prenda.ilike(like),
            OrdenProduccion.nombre_colegio.ilike(like),
            OrdenProduccion.taller.ilike(like),
        ))
    query = query.order_by(OrdenProduccion.numero.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'ordenes': [o.to_dict() for o in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
    }), 200


@ordenes_produccion_bp.route('/<int:id_orden>', methods=['GET'])
@admin_requerido
def detalle(id_orden):
    orden = OrdenProduccion.query.get_or_404(id_orden)
    return jsonify(orden.to_dict()), 200


@ordenes_produccion_bp.route('', methods=['POST'])
@admin_requerido
def crear():
    data = request.get_json() or {}

    prenda = (data.get('prenda') or '').strip()
    if not prenda:
        return jsonify({'error': 'La prenda es obligatoria'}), 400

    # Colegio (opcional): tomamos el nombre real de la BD si viene id
    id_colegio = data.get('id_colegio')
    nombre_colegio = (data.get('nombre_colegio') or '').strip()
    if id_colegio:
        col = Colegio.query.get(id_colegio)
        if col:
            nombre_colegio = col.nombre

    fecha_entrega = None
    if data.get('fecha_entrega'):
        from datetime import datetime
        try:
            fecha_entrega = datetime.strptime(data['fecha_entrega'][:10], '%Y-%m-%d').date()
        except ValueError:
            fecha_entrega = None

    # Consecutivo: max(numero)+1
    siguiente = (db.session.query(func.coalesce(func.max(OrdenProduccion.numero), 0)).scalar() or 0) + 1

    ident = get_current_identity()
    orden = OrdenProduccion(
        numero=siguiente,
        prenda=prenda,
        id_colegio=id_colegio,
        nombre_colegio=nombre_colegio,
        taller=(data.get('taller') or '').strip(),
        fecha_entrega=fecha_entrega,
        insumos_json=json.dumps(data.get('insumos') or [], ensure_ascii=False),
        tallas_json=json.dumps(data.get('tallas') or [], ensure_ascii=False),
        logo_descripcion=(data.get('logo_descripcion') or '').strip(),
        logo_ubicacion=(data.get('logo_ubicacion') or '').strip(),
        logo_tecnica=(data.get('logo_tecnica') or '').strip(),
        logo_tamano=(data.get('logo_tamano') or '').strip(),
        observaciones=(data.get('observaciones') or '').strip(),
        costo_tela=_f(data.get('costo_tela')),
        costo_insumos=_f(data.get('costo_insumos')),
        costo_mano_obra=_f(data.get('costo_mano_obra')),
        estado=data.get('estado') or 'creada',
        usuario_creacion=ident.get('usuario', ''),
    )
    db.session.add(orden)
    db.session.commit()
    registrar_auditoria('ordenes_produccion', orden.id_orden, 'CREAR',
                        f"Orden {orden.numero_fmt} — {prenda}")
    return jsonify(orden.to_dict()), 201


@ordenes_produccion_bp.route('/<int:id_orden>/estado', methods=['PUT'])
@admin_requerido
def cambiar_estado(id_orden):
    orden = OrdenProduccion.query.get_or_404(id_orden)
    nuevo = (request.get_json() or {}).get('estado', '').strip()
    if nuevo not in ('creada', 'enviada', 'recibida'):
        return jsonify({'error': 'Estado inválido'}), 400
    orden.estado = nuevo
    db.session.commit()
    return jsonify(orden.to_dict()), 200


@ordenes_produccion_bp.route('/<int:id_orden>', methods=['DELETE'])
@admin_requerido
def eliminar(id_orden):
    orden = OrdenProduccion.query.get_or_404(id_orden)
    numero = orden.numero_fmt
    db.session.delete(orden)
    db.session.commit()
    registrar_auditoria('ordenes_produccion', id_orden, 'ELIMINAR', f"Orden {numero}")
    return jsonify({'mensaje': 'Orden eliminada'}), 200


@ordenes_produccion_bp.route('/<int:id_orden>/pdf', methods=['GET'])
@admin_requerido
def pdf(id_orden):
    orden = OrdenProduccion.query.get_or_404(id_orden)
    buffer = generar_pdf_orden(orden)
    return send_file(
        buffer, mimetype='application/pdf', as_attachment=False,
        download_name=f"{orden.numero_fmt}.pdf",
    )
