"""
Avisos masivos enviados por WhatsApp: texto, a qué segmento y cuántos
llegaron o fallaron.
"""

from app import db
from datetime import datetime


class Aviso(db.Model):
    """Una nota/campaña enviada por WhatsApp a un segmento de clientes.
    Guarda el historial (qué se mandó, a cuántos, cuántos llegaron)."""
    __tablename__ = 'avisos'

    id_aviso = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.Text, nullable=False)
    segmento = db.Column(db.String(30))       # 'activos' | 'todos'
    total = db.Column(db.Integer, default=0)
    enviados = db.Column(db.Integer, default=0)
    fallidos = db.Column(db.Integer, default=0)
    autor = db.Column(db.String(80))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_aviso': self.id_aviso,
            'texto': self.texto,
            'segmento': self.segmento,
            'total': self.total,
            'enviados': self.enviados,
            'fallidos': self.fallidos,
            'autor': self.autor,
            'fecha': self.fecha.isoformat() + 'Z' if self.fecha else None,
        }
