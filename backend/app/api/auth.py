"""
API de Autenticación - JWT + Google OAuth
─────────────────────────────────────────
Tokens: identity=str(id_usuario), additional_claims={usuario, rol}
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt,
)
from app import db, limiter
from app.models.usuario import Usuario
from app.utils.decorators import get_current_identity
from app.utils.validators import validate_email, sanitize_string
import bcrypt
import os
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)


def _crear_tokens(usuario):
    """Helper: crear access + refresh token para un usuario"""
    claims = {'usuario': usuario.usuario, 'rol': usuario.rol}
    access_token = create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims=claims,
    )
    refresh_token = create_refresh_token(
        identity=str(usuario.id_usuario),
        additional_claims=claims,
    )
    return access_token, refresh_token


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login con usuario/email + contraseña"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    identificador = sanitize_string(data.get('usuario', ''), 100)
    password = data.get('password', '')

    if not identificador or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400

    # Buscar por usuario o email
    usuario = Usuario.query.filter(
        (Usuario.usuario == identificador) | (Usuario.email == identificador)
    ).first()

    if not usuario:
        return jsonify({'error': 'Credenciales inválidas'}), 401

    # Verificar si está bloqueado
    if usuario.bloqueado_hasta and usuario.bloqueado_hasta > datetime.utcnow():
        segundos = (usuario.bloqueado_hasta - datetime.utcnow()).seconds
        return jsonify({
            'error': f'Cuenta bloqueada. Intenta en {segundos} segundos',
            'bloqueado_hasta': usuario.bloqueado_hasta.isoformat()
        }), 429

    # Verificar contraseña
    if not bcrypt.checkpw(password.encode('utf-8'), usuario.contrasena_hash.encode('utf-8')):
        usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=5)
            usuario.intentos_fallidos = 0
        db.session.commit()
        return jsonify({'error': 'Credenciales inválidas'}), 401

    if not usuario.activo:
        return jsonify({'error': 'Cuenta desactivada. Contacta al administrador'}), 403

    # Login exitoso
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_login = datetime.utcnow()
    db.session.commit()

    access_token, refresh_token = _crear_tokens(usuario)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'usuario': usuario.to_dict(),
    }), 200


@auth_bp.route('/google', methods=['POST'])
@limiter.limit("10 per minute")
def google_login():
    """Login con Google OAuth"""
    data = request.get_json()
    token = data.get('credential')

    if not token:
        return jsonify({'error': 'Token de Google requerido'}), 400

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        client_id = os.getenv('GOOGLE_CLIENT_ID')
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id
        )

        google_id = idinfo['sub']
        email = idinfo.get('email')
        avatar = idinfo.get('picture')

        usuario = Usuario.query.filter(
            (Usuario.google_id == google_id) | (Usuario.email == email)
        ).first()

        if usuario:
            if not usuario.google_id:
                usuario.google_id = google_id
            if avatar:
                usuario.avatar_url = avatar
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
        else:
            return jsonify({
                'error': 'No hay una cuenta asociada a este correo. Contacta al administrador.'
            }), 403

        if not usuario.activo:
            return jsonify({'error': 'Cuenta desactivada'}), 403

        access_token, refresh_token = _crear_tokens(usuario)

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'usuario': usuario.to_dict(),
        }), 200

    except ValueError:
        return jsonify({'error': 'Token de Google inválido'}), 401


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renovar access token usando refresh token"""
    claims = get_jwt()
    id_usuario = int(claims['sub'])

    usuario = Usuario.query.filter_by(id_usuario=id_usuario).first()
    if not usuario or not usuario.activo:
        return jsonify({'error': 'Sesión inválida'}), 401

    new_claims = {'usuario': usuario.usuario, 'rol': usuario.rol}
    access_token = create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims=new_claims,
    )
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Obtener perfil del usuario actual"""
    identity = get_current_identity()
    usuario = Usuario.query.filter_by(id_usuario=identity['id_usuario']).first()
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({'usuario': usuario.to_dict()}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(verify_type=False)  # acepta token de acceso o de refresco
def logout():
    """Cierra sesión revocando el token actual (y el refresh si se envía)."""
    from app.models.token_revocado import TokenRevocado
    from datetime import datetime as _dt

    def _revocar(jti, exp_ts):
        if not jti:
            return
        if db.session.query(TokenRevocado.id).filter_by(jti=jti).first():
            return  # ya estaba revocado
        expira = _dt.utcfromtimestamp(exp_ts) if exp_ts else None
        db.session.add(TokenRevocado(jti=jti, expira=expira))

    # Revoca el token presentado en el header
    claims = get_jwt()
    _revocar(claims.get('jti'), claims.get('exp'))

    # Si el cliente manda el refresh_token, lo revoca también
    data = request.get_json(silent=True) or {}
    refresh = data.get('refresh_token')
    if refresh:
        try:
            from flask_jwt_extended import decode_token
            rt = decode_token(refresh)
            _revocar(rt.get('jti'), rt.get('exp'))
        except Exception:
            pass  # token inválido/expirado → nada que revocar

    db.session.commit()
    return jsonify({'message': 'Sesión cerrada'}), 200


@auth_bp.route('/cambiar-password', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    data = request.get_json()
    identity = get_current_identity()

    password_actual = data.get('password_actual', '')
    password_nuevo = data.get('password_nuevo', '')

    if not password_actual or not password_nuevo:
        return jsonify({'error': 'Ambas contraseñas requeridas'}), 400

    if len(password_nuevo) < 8:
        return jsonify({'error': 'La nueva contraseña debe tener mínimo 8 caracteres'}), 400

    usuario = Usuario.query.filter_by(id_usuario=identity['id_usuario']).first()
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if not bcrypt.checkpw(password_actual.encode('utf-8'), usuario.contrasena_hash.encode('utf-8')):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 401

    salt = bcrypt.gensalt(rounds=12)
    usuario.contrasena_hash = bcrypt.hashpw(password_nuevo.encode('utf-8'), salt).decode('utf-8')
    db.session.commit()

    return jsonify({'message': 'Contraseña actualizada'}), 200
