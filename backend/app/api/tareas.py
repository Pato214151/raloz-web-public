"""
API de Tareas para vendedores
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Tarea, Usuario
from app.utils.decorators import rol_requerido, get_current_identity
from app.utils.validators import sanitize_string, validate_date
from datetime import datetime

tareas_bp = Blueprint('tareas', __name__)


@tareas_bp.route('', methods=['GET'])
@jwt_required()
def listar_tareas():
    identity = get_current_identity()
    rol = identity.get('rol')
    id_usuario = identity.get('id_usuario')

    solo_pendientes = request.args.get('pendientes', 'false').lower() == 'true'

    query = Tarea.query

    # Vendedor solo ve sus tareas (asignadas a él o a todos)
    if rol == 'vendedor':
        query = query.filter(
            db.or_(Tarea.asignada_a == id_usuario, Tarea.asignada_a == None)
        )

    if solo_pendientes:
        query = query.filter(Tarea.completada == False)

    tareas = query.order_by(
        Tarea.completada.asc(),
        Tarea.fecha_vencimiento.asc().nullslast(),
        Tarea.fecha_creacion.desc()
    ).all()

    return jsonify([t.to_dict() for t in tareas])


@tareas_bp.route('', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def crear_tarea():
    identity = get_current_identity()
    data = request.get_json() or {}

    titulo = sanitize_string(data.get('titulo', ''), 200).strip()
    if not titulo:
        return jsonify({'error': 'El título es obligatorio'}), 400

    descripcion = sanitize_string(data.get('descripcion', ''), 1000).strip() or None
    fecha_venc = validate_date(data.get('fecha_vencimiento')) if data.get('fecha_vencimiento') else None
    asignada_a = data.get('asignada_a')  # None = todos

    if asignada_a:
        if not Usuario.query.get(asignada_a):
            return jsonify({'error': 'Usuario no encontrado'}), 404

    tarea = Tarea(
        titulo=titulo,
        descripcion=descripcion,
        fecha_vencimiento=fecha_venc,
        asignada_a=asignada_a if asignada_a else None,
        creada_por=identity['id_usuario'],
    )
    db.session.add(tarea)
    db.session.commit()
    return jsonify(tarea.to_dict()), 201


@tareas_bp.route('/<int:id_tarea>/completar', methods=['PATCH'])
@jwt_required()
def completar_tarea(id_tarea):
    identity = get_current_identity()
    id_usuario = identity.get('id_usuario')
    rol = identity.get('rol')

    tarea = Tarea.query.get_or_404(id_tarea)

    # Vendedor solo puede completar tareas que le corresponden
    if rol == 'vendedor':
        if tarea.asignada_a is not None and tarea.asignada_a != id_usuario:
            return jsonify({'error': 'No tienes permiso para esta tarea'}), 403

    tarea.completada = not tarea.completada
    if tarea.completada:
        tarea.completada_por = id_usuario
        tarea.fecha_completada = datetime.utcnow()
    else:
        tarea.completada_por = None
        tarea.fecha_completada = None

    db.session.commit()
    return jsonify(tarea.to_dict())


@tareas_bp.route('/<int:id_tarea>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def eliminar_tarea(id_tarea):
    tarea = Tarea.query.get_or_404(id_tarea)
    db.session.delete(tarea)
    db.session.commit()
    return jsonify({'ok': True})


@tareas_bp.route('/usuarios', methods=['GET'])
@jwt_required()
@rol_requerido('administrador')
def listar_usuarios_para_asignar():
    """Devuelve lista de usuarios activos para el selector de asignación"""
    usuarios = Usuario.query.filter_by(activo=True).order_by(Usuario.usuario).all()
    return jsonify([
        {'id_usuario': u.id_usuario, 'usuario': u.usuario, 'rol': u.rol}
        for u in usuarios
    ])
