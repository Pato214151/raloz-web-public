"""
Tokens JWT revocados (lista negra para logout real).

Cuando un usuario cierra sesión, el 'jti' (id único) de su token se guarda
aquí. En cada petición, el verificador de bloqueo (token_in_blocklist_loader)
revisa esta tabla; si el jti está, el token se rechaza aunque no haya expirado.
"""

from datetime import datetime
from app import db


class TokenRevocado(db.Model):
    __tablename__ = 'tokens_revocados'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expira = db.Column(db.DateTime, nullable=True)   # para limpiar los ya vencidos
    fecha_revocado = db.Column(db.DateTime, default=datetime.utcnow)
