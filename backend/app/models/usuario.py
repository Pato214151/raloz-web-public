from app import db
from datetime import datetime


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), default='vendedor')
    activo = db.Column(db.Boolean, default=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta = db.Column(db.DateTime, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'usuario': self.usuario,
            'email': self.email,
            'rol': self.rol,
            'activo': self.activo,
            'avatar_url': self.avatar_url,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }

    def to_dict_safe(self):
        """Sin datos sensibles"""
        return {
            'id_usuario': self.id_usuario,
            'usuario': self.usuario,
            'rol': self.rol,
            'activo': self.activo,
        }
