"""
API de Precios por Colegio
═════════════════════════════════════════════════════════════════

Maneja los precios de productos según el colegio y talla agrupada.
Los precios se definen por: colegio + producto + talla_grupo

Endpoints:
  GET    /precios?colegio_id=X - listar precios de un colegio
  GET    /precios/<colegio_id>/<producto_id> - precio específico
  POST   /precios - crear/actualizar precio
  PUT    /precios/bulk - actualización en lote
  DELETE /precios/<id_precio> - eliminar precio

Roles requeridos:
  - GET: cualquier usuario autenticado
  - POST/PUT/DELETE: administrador
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import PrecioColegio, Colegio, Producto
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import validate_required_fields, validate_positive_number, sanitize_string
from app.utils.tallas import validar_talla_grupo, obtener_tallas_agrupadas_validas

precios_bp = Blueprint('precios', __name__)


@precios_bp.route('', methods=['GET'])
@jwt_required()
def listar_precios():
    """
    Listar precios de un colegio.

    Query params:
      - colegio_id (int, requerido): ID del colegio
      - producto_id (int, opcional): filtrar por producto
      - talla_grupo (str, opcional): filtrar por talla agrupada
      - page (int, default=1): número de página
      - per_page (int, default=20, max=100): items por página

    Response:
      {
        "precios": [
          {
            "id_precio": 1,
            "id_colegio": 5,
            "id_producto": 10,
            "producto_nombre": "Uniforme Niño",
            "talla_grupo": "6-8",
            "precio_unitario": 45000
          },
          ...
        ],
        "total": 150,
        "pages": 8,
        "page": 1
      }
    """
    colegio_id = request.args.get('colegio_id', type=int)
    producto_id = request.args.get('producto_id', type=int)
    talla_grupo = request.args.get('talla_grupo', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    if not colegio_id:
        return jsonify({'error': 'colegio_id es requerido'}), 400

    # Verificar que el colegio existe
    colegio = Colegio.query.get(colegio_id)
    if not colegio:
        return jsonify({'error': f'Colegio {colegio_id} no existe'}), 404

    query = PrecioColegio.query.filter(PrecioColegio.id_colegio == colegio_id)

    if producto_id:
        query = query.filter(PrecioColegio.id_producto == producto_id)

    if talla_grupo:
        if not validar_talla_grupo(talla_grupo):
            return jsonify({'error': f'Talla agrupada inválida: {talla_grupo}'}), 400
        query = query.filter(PrecioColegio.talla_grupo == talla_grupo)

    query = query.order_by(PrecioColegio.id_producto, PrecioColegio.talla_grupo)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'precios': [{
            'id_precio': p.id_precio,
            'id_colegio': p.id_colegio,
            'colegio_nombre': p.colegio.nombre if p.colegio else None,
            'id_producto': p.id_producto,
            'producto_nombre': p.producto.nombre if p.producto else None,
            'talla_grupo': p.talla_grupo,
            'precio_unitario': p.precio_unitario,
        } for p in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page': page,
    }), 200


@precios_bp.route('/<int:colegio_id>/<int:producto_id>', methods=['GET'])
@jwt_required()
def obtener_precios_producto(colegio_id, producto_id):
    """
    Obtener todos los precios de un producto en un colegio.

    Returns:
      {
        "id_colegio": 5,
        "colegio_nombre": "Colegio A",
        "id_producto": 10,
        "producto_nombre": "Uniforme Niño",
        "precios": [
          {"talla_grupo": "6-8", "precio_unitario": 45000},
          {"talla_grupo": "10-12", "precio_unitario": 48000},
          ...
        ]
      }
    """
    colegio = Colegio.query.get_or_404(colegio_id)
    producto = Producto.query.get_or_404(producto_id)

    precios = PrecioColegio.query.filter(
        (PrecioColegio.id_colegio == colegio_id) &
        (PrecioColegio.id_producto == producto_id)
    ).order_by(PrecioColegio.talla_grupo).all()

    if not precios:
        return jsonify({
            'id_colegio': colegio_id,
            'colegio_nombre': colegio.nombre,
            'id_producto': producto_id,
            'producto_nombre': producto.nombre,
            'precios': [],
            'message': 'No hay precios configurados para este producto en este colegio',
        }), 200

    return jsonify({
        'id_colegio': colegio_id,
        'colegio_nombre': colegio.nombre,
        'id_producto': producto_id,
        'producto_nombre': producto.nombre,
        'precios': [{
            'talla_grupo': p.talla_grupo,
            'precio_unitario': p.precio_unitario,
        } for p in precios],
    }), 200


@precios_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def crear_precio():
    """
    Crear o actualizar un precio.

    Body JSON:
      {
        "id_colegio": 5,
        "id_producto": 10,
        "talla_grupo": "6-8",
        "precio_unitario": 45000
      }

    Returns:
      201 (nuevo) o 200 (actualizado)
    """
    data = request.get_json()
    identity = get_current_identity()

    # Validar campos requeridos
    ok, msg = validate_required_fields(data, ['id_colegio', 'id_producto', 'talla_grupo', 'precio_unitario'])
    if not ok:
        return jsonify({'error': msg}), 400

    colegio_id = data.get('id_colegio')
    producto_id = data.get('id_producto')
    talla_grupo = str(data.get('talla_grupo', '')).strip()
    precio_unitario = data.get('precio_unitario')

    # Validar que colegio y producto existen
    if not Colegio.query.get(colegio_id):
        return jsonify({'error': f'Colegio {colegio_id} no existe'}), 404
    if not Producto.query.get(producto_id):
        return jsonify({'error': f'Producto {producto_id} no existe'}), 404

    # Validar talla
    if not validar_talla_grupo(talla_grupo):
        return jsonify({
            'error': f'Talla agrupada inválida: {talla_grupo}',
            'tallas_validas': obtener_tallas_agrupadas_validas(),
        }), 400

    # Validar precio
    if not validate_positive_number(precio_unitario):
        return jsonify({'error': 'Precio unitario debe ser un número positivo'}), 400

    # Buscar precio existente
    precio = PrecioColegio.query.filter(
        (PrecioColegio.id_colegio == colegio_id) &
        (PrecioColegio.id_producto == producto_id) &
        (PrecioColegio.talla_grupo == talla_grupo)
    ).first()

    es_nuevo = precio is None
    if es_nuevo:
        precio = PrecioColegio(
            id_colegio=colegio_id,
            id_producto=producto_id,
            talla_grupo=talla_grupo,
            precio_unitario=float(precio_unitario),
        )
        db.session.add(precio)
        accion = 'CREAR'
    else:
        precio.precio_unitario = float(precio_unitario)
        accion = 'ACTUALIZAR'

    db.session.commit()

    registrar_auditoria(
        'precios_colegio',
        precio.id_precio,
        accion,
        f'Precio {accion.lower()} por {identity["usuario"]}: ${precio_unitario}'
    )

    return jsonify({
        'message': 'Precio creado' if es_nuevo else 'Precio actualizado',
        'precio': {
            'id_precio': precio.id_precio,
            'id_colegio': precio.id_colegio,
            'id_producto': precio.id_producto,
            'talla_grupo': precio.talla_grupo,
            'precio_unitario': precio.precio_unitario,
        },
    }), 201 if es_nuevo else 200


@precios_bp.route('/bulk', methods=['PUT'])
@jwt_required()
@rol_requerido('administrador')
def actualizar_precios_bulk():
    """
    Actualización en lote de precios.

    Body JSON:
      {
        "precios": [
          {
            "id_colegio": 5,
            "id_producto": 10,
            "talla_grupo": "6-8",
            "precio_unitario": 45000
          },
          ...
        ]
      }

    Returns:
      {
        "creados": 3,
        "actualizados": 5,
        "errores": [
          {"index": 1, "error": "..."}
        ],
        "precios": [...]
      }
    """
    data = request.get_json()
    identity = get_current_identity()

    if not data.get('precios') or not isinstance(data['precios'], list):
        return jsonify({'error': 'precios debe ser una lista'}), 400

    creados = 0
    actualizados = 0
    errores = []
    precios_result = []

    for idx, item in enumerate(data['precios']):
        try:
            # Validar
            colegio_id = item.get('id_colegio')
            producto_id = item.get('id_producto')
            talla_grupo = str(item.get('talla_grupo', '')).strip()
            precio_unitario = item.get('precio_unitario')

            if not all([colegio_id, producto_id, talla_grupo, precio_unitario]):
                raise ValueError('Campos requeridos faltantes')

            if not Colegio.query.get(colegio_id):
                raise ValueError(f'Colegio {colegio_id} no existe')
            if not Producto.query.get(producto_id):
                raise ValueError(f'Producto {producto_id} no existe')
            if not validar_talla_grupo(talla_grupo):
                raise ValueError(f'Talla agrupada inválida: {talla_grupo}')
            if not validate_positive_number(precio_unitario):
                raise ValueError('Precio unitario debe ser positivo')

            # Buscar o crear
            precio = PrecioColegio.query.filter(
                (PrecioColegio.id_colegio == colegio_id) &
                (PrecioColegio.id_producto == producto_id) &
                (PrecioColegio.talla_grupo == talla_grupo)
            ).first()

            if precio:
                precio.precio_unitario = float(precio_unitario)
                actualizados += 1
                accion = 'ACTUALIZAR'
            else:
                precio = PrecioColegio(
                    id_colegio=colegio_id,
                    id_producto=producto_id,
                    talla_grupo=talla_grupo,
                    precio_unitario=float(precio_unitario),
                )
                db.session.add(precio)
                creados += 1
                accion = 'CREAR'

            precios_result.append({
                'id_precio': precio.id_precio,
                'id_colegio': precio.id_colegio,
                'id_producto': precio.id_producto,
                'talla_grupo': precio.talla_grupo,
                'precio_unitario': precio.precio_unitario,
            })

        except Exception as e:
            errores.append({'index': idx, 'error': str(e)})

    db.session.commit()

    for precio in precios_result:
        registrar_auditoria(
            'precios_colegio',
            precio['id_precio'],
            'ACTUALIZAR_BULK',
            f'Actualización masiva por {identity["usuario"]}'
        )

    return jsonify({
        'message': f'Actualización en lote completada: {creados} creados, {actualizados} actualizados',
        'creados': creados,
        'actualizados': actualizados,
        'errores': errores,
        'precios': precios_result,
    }), 200


@precios_bp.route('/<int:id_precio>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_precio(id_precio):
    """Eliminar un precio."""
    precio = PrecioColegio.query.get_or_404(id_precio)
    identity = get_current_identity()

    id_colegio = precio.id_colegio
    id_producto = precio.id_producto
    talla_grupo = precio.talla_grupo

    db.session.delete(precio)
    db.session.commit()

    registrar_auditoria(
        'precios_colegio',
        id_precio,
        'ELIMINAR',
        f'Precio eliminado por {identity["usuario"]}: colegio={id_colegio}, producto={id_producto}, talla={talla_grupo}'
    )

    return jsonify({'message': 'Precio eliminado correctamente'}), 200
