"""
Decoradores de seguridad y autorización
─────────────────────────────────────────
JWT approach:
  - identity (sub) = str(id_usuario)  → siempre string
  - claims adicionales = {usuario, rol} → via additional_claims
  - get_jwt() retorna todo el payload incluyendo sub, usuario, rol
"""

from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def get_current_identity():
    """
    Obtener identity del usuario actual desde el JWT.
    Retorna dict: {id_usuario: int, usuario: str, rol: str}
    """
    claims = get_jwt()
    return {
        'id_usuario': int(claims['sub']),
        'usuario': claims.get('usuario', ''),
        'rol': claims.get('rol', ''),
    }


def rol_requerido(*roles_permitidos):
    """Decorador que verifica que el usuario tenga uno de los roles permitidos"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            rol = claims.get('rol', '')
            if rol not in roles_permitidos:
                return jsonify({'error': 'No tienes permiso para esta acción'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_requerido(fn):
    """Solo administradores"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('rol') != 'administrador':
            return jsonify({'error': 'Acceso solo para administradores'}), 403
        return fn(*args, **kwargs)
    return wrapper


def registrar_auditoria(tabla, id_registro, accion, comentario=None):
    """Registrar acción en tabla de auditoría"""
    from app import db
    from app.models.auditoria import Auditoria

    try:
        claims = get_jwt()
        usuario_nombre = claims.get('usuario', 'sistema')
    except Exception:
        usuario_nombre = 'sistema'

    audit = Auditoria(
        tabla_afectada=tabla,
        id_registro=id_registro,
        accion=accion,
        usuario=usuario_nombre,
        comentario=comentario,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(audit)
    db.session.commit()
