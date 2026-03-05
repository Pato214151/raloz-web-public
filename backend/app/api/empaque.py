"""
API de Empaque / Revisión de Prendas
═════════════════════════════════════════════════════════════════

Maneja el flujo de revisión y empaque de prendas antes de la entrega.
Permite:
  1. Ver detalles de una factura para revisar prendas
  2. Registrar prendas pendientes de una factura
  3. Marcar factura completa como lista para empaque

Endpoints:
  GET    /empaque/factura/<numero> - obtener detalles de factura
  POST   /empaque/registrar - registrar prendas pendientes de una factura
  POST   /empaque/todo-listo/<id_factura> - marcar factura como completa

Roles requeridos:
  - GET: cualquier usuario autenticado
  - POST: administrador, vendedor
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Factura, FacturaDetalle, PrendaPendiente, StockPendiente
from app.utils.decorators import rol_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import validate_required_fields, validate_positive_number
from datetime import date

empaque_bp = Blueprint('empaque', __name__)


@empaque_bp.route('/factura/<numero>', methods=['GET'])
@jwt_required()
def obtener_factura_empaque(numero):
    """
    Obtener detalles de una factura para revisión de empaque.

    Response:
      {
        "factura": {
          "id_factura": 5,
          "numero_factura": "FAC-2026-000001",
          "cliente_nombre": "Juan Pérez",
          "colegio_nombre": "Colegio A",
          "total": 150000,
          "estado": "PAGADA",
          "estado_entrega": "POR_ENTREGAR",
          "detalles": [
            {
              "id_detalle": 1,
              "producto_nombre": "Uniforme Niño",
              "talla": "8",
              "cantidad": 2,
              "precio_unitario": 45000,
              "subtotal": 90000
            },
            ...
          ]
        },
        "prendas_pendientes": [
          {
            "id_pendiente": 1,
            "producto_nombre": "Uniforme Niño",
            "talla": "8",
            "cantidad": 1,
            "estado": "PENDIENTE",
            "fecha_registro": "2026-02-25"
          },
          ...
        ]
      }
    """
    factura = Factura.query.filter(Factura.numero_factura.ilike(f'%{numero}%')).first_or_404()

    detalles = []
    for detalle in factura.detalles:
        detalles.append({
            'id_detalle': detalle.id_detalle if hasattr(detalle, 'id_detalle') else None,
            'id_producto': detalle.id_producto,
            'producto_nombre': detalle.producto.nombre if detalle.producto else None,
            'talla': detalle.talla_individual,
            'cantidad': detalle.cantidad,
            'precio_unitario': detalle.precio_unitario,
            'subtotal': detalle.total_linea,
        })

    # Buscar prendas pendientes de esta factura
    prendas_pendientes = PrendaPendiente.query.filter(
        PrendaPendiente.id_factura == factura.id_factura
    ).all()

    return jsonify({
        'factura': {
            'id_factura': factura.id_factura,
            'numero_factura': factura.numero_factura,
            'cliente_nombre': factura.cliente_nombre,
            'colegio_nombre': factura.colegio.nombre if factura.colegio else None,
            'total': factura.total,
            'estado': factura.estado,
            'estado_entrega': factura.estado_entrega,
            'genero_estudiante': factura.genero_estudiante,
            'fecha_factura': factura.fecha_factura.isoformat() if factura.fecha_factura else None,
            'detalles': detalles,
        },
        'prendas_pendientes': [p.to_dict() for p in prendas_pendientes],
    }), 200


@empaque_bp.route('/registrar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def registrar_prendas_empaque():
    """
    Registrar prendas pendientes de una factura.

    Body JSON:
      {
        "id_factura": 5,
        "prendas": [
          {
            "producto_nombre": "Uniforme Niño",
            "talla": "8",
            "cantidad": 1,
            "observaciones": "Sin costuras"
          },
          ...
        ]
      }

    Returns:
      {
        "message": "2 prendas registradas",
        "prendas_registradas": 2,
        "prendas": [...]
      }
    """
    data = request.get_json()
    identity = get_current_identity()

    ok, msg = validate_required_fields(data, ['id_factura', 'prendas'])
    if not ok:
        return jsonify({'error': msg}), 400

    id_factura = data.get('id_factura')
    prendas = data.get('prendas', [])

    # Verificar que la factura existe
    factura = Factura.query.get_or_404(id_factura)

    if not isinstance(prendas, list) or len(prendas) == 0:
        return jsonify({'error': 'prendas debe ser una lista no vacía'}), 400

    prendas_registradas = 0
    prendas_result = []

    for prenda_data in prendas:
        try:
            producto_nombre = prenda_data.get('producto_nombre', '').strip()
            talla = prenda_data.get('talla', '').strip()
            cantidad = prenda_data.get('cantidad', 1)
            observaciones = prenda_data.get('observaciones', '').strip()

            if not producto_nombre:
                continue
            if not validate_positive_number(cantidad):
                continue

            genero = prenda_data.get('genero', '').strip() or factura.genero_estudiante or 'NIÑO'

            prenda = PrendaPendiente(
                id_factura=id_factura,
                numero_factura=factura.numero_factura,
                id_colegio=factura.id_colegio,
                colegio_nombre=factura.colegio.nombre if factura.colegio else None,
                cliente_nombre=factura.cliente_nombre,
                producto_nombre=producto_nombre,
                talla=talla,
                cantidad=int(cantidad),
                genero=genero,
                estado='PENDIENTE',
                fecha_registro=date.today(),
                fecha_factura=factura.fecha_factura,
                observaciones=observaciones,
                usuario_registro=identity['usuario'],
            )
            db.session.add(prenda)
            prendas_registradas += 1
            prendas_result.append(prenda.to_dict())

        except Exception as e:
            continue

    db.session.commit()

    registrar_auditoria(
        'prendas_pendientes',
        id_factura,
        'REGISTRAR',
        f'{prendas_registradas} prendas registradas por {identity["usuario"]}'
    )

    return jsonify({
        'message': f'{prendas_registradas} prendas registradas',
        'prendas_registradas': prendas_registradas,
        'prendas': prendas_result,
    }), 201


@empaque_bp.route('/todo-listo/<int:id_factura>', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def marcar_factura_completa(id_factura):
    """
    Marcar una factura como lista para empaque (todas las prendas revisadas).

    Body JSON (opcional):
      {
        "observaciones": "Todas las prendas listas"
      }

    Response:
      {
        "message": "Factura marcada como lista para empaque",
        "factura": {
          "id_factura": 5,
          "numero_factura": "FAC-2026-000001",
          "estado_entrega": "LISTO_EMPAQUE"
        }
      }
    """
    factura = Factura.query.get_or_404(id_factura)
    identity = get_current_identity()
    data = request.get_json() or {}

    # Cambiar estado — acepta desde cualquier estado previo a LISTO_EMPAQUE
    factura.estado_entrega = 'LISTO_EMPAQUE'
    observaciones = data.get('observaciones', '')

    db.session.commit()

    registrar_auditoria(
        'facturas',
        id_factura,
        'LISTO_EMPAQUE',
        f'Factura marcada lista para empaque por {identity["usuario"]}. {observaciones}' if observaciones else f'Factura marcada lista para empaque por {identity["usuario"]}'
    )

    return jsonify({
        'message': 'Factura marcada como lista para empaque',
        'factura': {
            'id_factura': factura.id_factura,
            'numero_factura': factura.numero_factura,
            'estado_entrega': factura.estado_entrega,
        },
    }), 200


@empaque_bp.route('/listo-llamar/<int:id_factura>', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor')
def marcar_listo_llamar(id_factura):
    """Marcar un paquete como listo para llamar al cliente"""
    factura = Factura.query.get_or_404(id_factura)
    identity = get_current_identity()

    factura.estado_entrega = 'LISTO_LLAMAR'
    db.session.commit()

    registrar_auditoria('facturas', id_factura, 'LISTO_LLAMAR',
                        f'Paquete listo para llamar. Marcado por {identity["usuario"]}')

    return jsonify({
        'message': 'Paquete marcado como listo para llamar',
        'factura': {
            'id_factura': factura.id_factura,
            'numero_factura': factura.numero_factura,
            'cliente_nombre': factura.cliente_nombre,
            'cliente_telefono': factura.cliente_telefono,
            'colegio_nombre': factura.colegio.nombre if factura.colegio else None,
            'estado_entrega': factura.estado_entrega,
        },
    }), 200


@empaque_bp.route('/listos-llamar', methods=['GET'])
@jwt_required()
def listar_listos_llamar():
    """Listar todos los paquetes listos para llamar al cliente"""
    facturas = Factura.query.filter_by(estado_entrega='LISTO_LLAMAR') \
        .order_by(Factura.fecha_creacion.desc()).all()

    return jsonify([{
        'id_factura': f.id_factura,
        'numero_factura': f.numero_factura,
        'cliente_nombre': f.cliente_nombre,
        'cliente_telefono': f.cliente_telefono,
        'colegio_nombre': f.colegio.nombre if f.colegio else None,
        'fecha_factura': f.fecha_factura.isoformat() if f.fecha_factura else None,
        'total': f.total,
        'saldo_pendiente': f.saldo_pendiente,
    } for f in facturas])
