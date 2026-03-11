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
from sqlalchemy import text

tareas_bp = Blueprint('tareas', __name__)

# Cache: evita consultar la BD en cada request
_prioridad_existe = None


def _tiene_columna_prioridad():
    global _prioridad_existe
    if _prioridad_existe is not None:
        return _prioridad_existe
    try:
        db.session.execute(text("SELECT prioridad FROM tareas LIMIT 1"))
        _prioridad_existe = True
    except Exception:
        db.session.rollback()
        _prioridad_existe = False
    return _prioridad_existe


def _row_to_dict(row):
    keys = list(row._fields) if hasattr(row, '_fields') else list(row.keys())
    d = dict(zip(keys, tuple(row)))
    for k in ('fecha_vencimiento', 'fecha_completada', 'fecha_creacion'):
        val = d.get(k)
        if val and hasattr(val, 'isoformat'):
            d[k] = val.isoformat()
        elif val is None:
            d[k] = None
    d.setdefault('prioridad', 'MEDIA')
    d.setdefault('asignada_a_nombre', None)
    d.setdefault('creada_por_nombre', None)
    d.setdefault('completada_por_nombre', None)
    return d


def _tareas_sql(filtro_usuario_id=None, solo_pendientes=False, id_tarea=None):
    """SQL directo para cuando no existe la columna prioridad"""
    where = []
    params = {}
    if filtro_usuario_id is not None:
        where.append("(t.asignada_a = :uid OR t.asignada_a IS NULL)")
        params['uid'] = filtro_usuario_id
    if solo_pendientes:
        where.append("t.completada = false")
    if id_tarea is not None:
        where.append("t.id_tarea = :id_tarea")
        params['id_tarea'] = id_tarea

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = text(f"""
        SELECT t.id_tarea, t.titulo, t.descripcion,
               t.fecha_vencimiento, t.asignada_a, t.creada_por,
               t.completada, t.completada_por,
               t.fecha_completada, t.fecha_creacion,
               u1.usuario AS asignada_a_nombre,
               u2.usuario AS creada_por_nombre,
               u3.usuario AS completada_por_nombre
        FROM tareas t
        LEFT JOIN usuarios u1 ON t.asignada_a = u1.id_usuario
        LEFT JOIN usuarios u2 ON t.creada_por = u2.id_usuario
        LEFT JOIN usuarios u3 ON t.completada_por = u3.id_usuario
        {where_sql}
        ORDER BY t.completada ASC, t.fecha_creacion DESC
    """)
    rows = db.session.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


@tareas_bp.route('', methods=['GET'])
@jwt_required()
def listar_tareas():
    identity = get_current_identity()
    rol = identity.get('rol')
    id_usuario = identity.get('id_usuario')
    solo_pendientes = request.args.get('pendientes', 'false').lower() == 'true'

    if not _tiene_columna_prioridad():
        uid = id_usuario if rol == 'vendedor' else None
        return jsonify(_tareas_sql(filtro_usuario_id=uid, solo_pendientes=solo_pendientes))

    query = Tarea.query
    if rol == 'vendedor':
        query = query.filter(
            db.or_(Tarea.asignada_a == id_usuario, Tarea.asignada_a == None)
        )
    if solo_pendientes:
        query = query.filter(Tarea.completada == False)

    from sqlalchemy import case
    prioridad_order = case(
        (Tarea.prioridad == 'ALTA', 1),
        (Tarea.prioridad == 'MEDIA', 2),
        (Tarea.prioridad == 'BAJA', 3),
        else_=2
    )
    tareas = query.order_by(
        Tarea.completada.asc(),
        prioridad_order.asc(),
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
    asignada_a = data.get('asignada_a')
    prioridad = sanitize_string(data.get('prioridad', 'MEDIA'), 10)
    if prioridad not in ('ALTA', 'MEDIA', 'BAJA'):
        prioridad = 'MEDIA'

    if asignada_a:
        if not Usuario.query.get(asignada_a):
            return jsonify({'error': 'Usuario no encontrado'}), 404

    if not _tiene_columna_prioridad():
        # INSERT sin columna prioridad
        sql = text("""
            INSERT INTO tareas (titulo, descripcion, fecha_vencimiento, asignada_a, creada_por, completada, fecha_creacion)
            VALUES (:titulo, :descripcion, :fecha_venc, :asignada_a, :creada_por, false, NOW())
            RETURNING id_tarea
        """)
        result = db.session.execute(sql, {
            'titulo': titulo, 'descripcion': descripcion,
            'fecha_venc': fecha_venc, 'asignada_a': asignada_a if asignada_a else None,
            'creada_por': identity['id_usuario'],
        })
        db.session.commit()
        id_nuevo = result.fetchone()[0]
        rows = _tareas_sql(id_tarea=id_nuevo)
        return jsonify(rows[0] if rows else {}), 201

    try:
        tarea = Tarea(
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            fecha_vencimiento=fecha_venc,
            asignada_a=asignada_a if asignada_a else None,
            creada_por=identity['id_usuario'],
        )
        db.session.add(tarea)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar tarea: {str(e)}'}), 500

    return jsonify(tarea.to_dict()), 201


@tareas_bp.route('/<int:id_tarea>/completar', methods=['PATCH'])
@jwt_required()
def completar_tarea(id_tarea):
    identity = get_current_identity()
    id_usuario = identity.get('id_usuario')
    rol = identity.get('rol')

    if not _tiene_columna_prioridad():
        # Usar SQL directo
        row = db.session.execute(
            text("SELECT id_tarea, asignada_a, completada FROM tareas WHERE id_tarea = :id"),
            {'id': id_tarea}
        ).fetchone()
        if not row:
            return jsonify({'error': 'Tarea no encontrada'}), 404
        if rol == 'vendedor' and row[1] is not None and row[1] != id_usuario:
            return jsonify({'error': 'No tienes permiso para esta tarea'}), 403

        nueva_completada = not row[2]
        ahora = datetime.utcnow() if nueva_completada else None
        cp = id_usuario if nueva_completada else None
        db.session.execute(text("""
            UPDATE tareas SET completada = :c, completada_por = :cp, fecha_completada = :fc
            WHERE id_tarea = :id
        """), {'c': nueva_completada, 'cp': cp, 'fc': ahora, 'id': id_tarea})
        db.session.commit()
        rows = _tareas_sql(id_tarea=id_tarea)
        return jsonify(rows[0] if rows else {})

    tarea = Tarea.query.get_or_404(id_tarea)
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
    if not _tiene_columna_prioridad():
        result = db.session.execute(
            text("DELETE FROM tareas WHERE id_tarea = :id"), {'id': id_tarea}
        )
        db.session.commit()
        if result.rowcount == 0:
            return jsonify({'error': 'Tarea no encontrada'}), 404
        return jsonify({'ok': True})

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
