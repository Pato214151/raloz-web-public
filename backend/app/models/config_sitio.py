"""
Configuración de la tienda en línea guardada como clave/valor
(banner, textos, interruptores).
"""

from app import db
from datetime import datetime


class ConfigSitio(db.Model):
    """Ajustes del sitio editables desde el panel (clave → valor).
    Ej: banner_texto, banner_activo. Se sirve a la tienda pública por API.
    """
    __tablename__ = 'config_sitio'

    clave = db.Column(db.String(60), primary_key=True)
    valor = db.Column(db.Text)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow,
                               onupdate=datetime.utcnow)

    def to_dict(self):
        return {'clave': self.clave, 'valor': self.valor}

    @staticmethod
    def get(clave, default=None):
        row = ConfigSitio.query.get(clave)
        return row.valor if row and row.valor is not None else default

    @staticmethod
    def set(clave, valor):
        row = ConfigSitio.query.get(clave)
        if row:
            row.valor = valor
        else:
            row = ConfigSitio(clave=clave, valor=valor)
            db.session.add(row)
        return row
