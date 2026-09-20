"""
Personas suscritas a los avisos por WhatsApp (con su autorización de datos).
"""

from app import db
from datetime import datetime


class Suscriptor(db.Model):
    """Cliente que aceptó recibir información/ofertas (consentimiento Ley 1581).
    Se captura desde la tienda; alimenta el segmento 'suscriptores' de los avisos."""
    __tablename__ = 'suscriptores'

    id_suscriptor = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(40), unique=True, nullable=False)
    nombre = db.Column(db.String(160))
    acepta_datos = db.Column(db.Boolean, default=True)   # autorización explícita
    activo = db.Column(db.Boolean, default=True)         # False = se dio de baja
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_suscriptor': self.id_suscriptor,
            'telefono': self.telefono,
            'nombre': self.nombre,
            'acepta_datos': bool(self.acepta_datos),
            'activo': bool(self.activo),
            'fecha': self.fecha.isoformat() + 'Z' if self.fecha else None,
        }
