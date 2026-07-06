"""
API de Gestión de Usuarios (Admin)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Usuario, Factura
from app.utils.decorators import admin_requerido, registrar_auditoria, get_current_identity
from app.utils.validators import sanitize_string, validate_email
from sqlalchemy import func, and_
from datetime import date, timedelta
import bcrypt

usuarios_bp = Blueprint('usuarios', __name__)


@usuarios_bp.route('', methods=['GET'])
@jwt_required()
@admin_requerido
def listar_usuarios():
    """Listar todos los usuarios"""
    usuarios = Usuario.query.order_by(Usuario.usuario).all()
    return jsonify({'usuarios': [u.to_dict() for u in usuarios]}), 200


@usuarios_bp.route('/<int:id_usuario>/actividad', methods=['GET'])
@jwt_required()
@admin_requerido
def actividad_usuario(id_usuario):
    """Ver actividad de un usuario (ventas, KPIs)"""
    usuario = Usuario.query.get_or_404(id_usuario)
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    def ventas_periodo(desde, hasta):
        result = db.session.query(
            func.count(Factura.id_factura),
            func.coalesce(func.sum(Factura.total), 0),
        ).filter(and_(
            Factura.usuario_creacion == usuario.usuario,
            Factura.fecha_factura >= desde,
            Factura.fecha_factura <= hasta,
            Factura.estado != 'ANULADA',
        )).first()
        return {'facturas': result[0], 'total': float(result[1])}

    # KPIs
    kpis = {
        'hoy': ventas_periodo(hoy, hoy),
        'ayer': ventas_periodo(ayer, ayer),
        'semana': ventas_periodo(inicio_semana, hoy),
        'mes': ventas_periodo(inicio_mes, hoy),
    }

    # Últimas 30 facturas
    ultimas = Factura.query.filter_by(
        usuario_creacion=usuario.usuario
    ).order_by(Factura.fecha_creacion.desc()).limit(30).all()

    # Desglose últimos 7 días
    desglose = []
    for i in range(7):
        dia = hoy - timedelta(days=i)
        info = ventas_periodo(dia, dia)
        desglose.append({'fecha': dia.isoformat(), **info})

    return jsonify({
        'usuario': usuario.to_dict(),
        'kpis': kpis,
        'desglose_7_dias': desglose,
        'ultimas_facturas': [f.to_dict() for f in ultimas],
    }), 200


@usuarios_bp.route('', methods=['POST'])
@jwt_required()
@admin_requerido
def crear_usuario():
    """Crear nuevo usuario"""
    data = request.get_json()
    identity = get_current_identity()

    nombre_usuario = sanitize_string(data.get('usuario', ''), 100)
    password = data.get('password', '')
    rol = data.get('rol', 'vendedor')
    email = sanitize_string(data.get('email', ''), 255)

    if not nombre_usuario or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Contraseña mínimo 6 caracteres'}), 400

    if rol not in ('administrador', 'vendedor', 'cajero'):
        return jsonify({'error': 'Rol inválido'}), 400

    if email and not validate_email(email):
        return jsonify({'error': 'Email inválido'}), 400

    existente = Usuario.query.filter_by(usuario=nombre_usuario).first()
    if existente:
        return jsonify({'error': 'Ese nombre de usuario ya existe'}), 409

    salt = bcrypt.gensalt(rounds=12)
    hash_pw = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    usuario = Usuario(
        usuario=nombre_usuario,
        email=email or None,
        contrasena_hash=hash_pw,
        rol=rol,
    )
    db.session.add(usuario)
    db.session.commit()
    registrar_auditoria('usuarios', usuario.id_usuario, 'CREAR', f'Nuevo usuario: {nombre_usuario} ({rol})')

    return jsonify({'message': 'Usuario creado', 'usuario': usuario.to_dict()}), 201


@usuarios_bp.route('/<int:id_usuario>/password', methods=['POST'])
@jwt_required()
@admin_requerido
def cambiar_password_admin(id_usuario):
    """Admin cambia contraseña de un usuario"""
    data = request.get_json()
    nuevo_password = data.get('password', '')

    if len(nuevo_password) < 6:
        return jsonify({'error': 'Contraseña mínimo 6 caracteres'}), 400

    usuario = Usuario.query.get_or_404(id_usuario)
    salt = bcrypt.gensalt(rounds=12)
    usuario.contrasena_hash = bcrypt.hashpw(nuevo_password.encode('utf-8'), salt).decode('utf-8')
    db.session.commit()

    return jsonify({'message': f'Contraseña de {usuario.usuario} actualizada'}), 200


@usuarios_bp.route('/<int:id_usuario>/toggle', methods=['POST'])
@jwt_required()
@admin_requerido
def toggle_usuario(id_usuario):
    """Activar/Desactivar usuario"""
    identity = get_current_identity()
    usuario = Usuario.query.get_or_404(id_usuario)

    if usuario.id_usuario == identity['id_usuario']:
        return jsonify({'error': 'No puedes desactivarte a ti mismo'}), 400

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    return jsonify({'message': f'Usuario {estado}', 'usuario': usuario.to_dict()}), 200
