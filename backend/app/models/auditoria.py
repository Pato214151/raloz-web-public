"""
Auditoría: qué tabla y registro se tocó, qué acción, quién y desde qué IP.
"""

from app import db
from datetime import datetime


class Auditoria(db.Model):
    __tablename__ = 'auditoria'

    id_auditoria = db.Column(db.Integer, primary_key=True)
    tabla_afectada = db.Column(db.String(100), nullable=False)
    id_registro = db.Column(db.Integer)
    accion = db.Column(db.String(50), nullable=False)
    usuario = db.Column(db.String(100), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    comentario = db.Column(db.Text)
    ip_address = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id_auditoria': self.id_auditoria,
            'tabla_afectada': self.tabla_afectada,
            'id_registro': self.id_registro,
            'accion': self.accion,
            'usuario': self.usuario,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None,
            'comentario': self.comentario,
        }
