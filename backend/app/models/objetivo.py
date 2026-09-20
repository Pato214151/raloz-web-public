"""
Metas del negocio (por mes o año) que el asistente usa para comparar.
"""

from app import db
from datetime import datetime


class Objetivo(db.Model):
    """Meta empresarial persistente (Persistent Goals).
    Ej: 'Vender $30.000.000 en septiembre'. El progreso se calcula en vivo
    contra las ventas reales; no se guarda."""
    __tablename__ = 'objetivos'

    id_objetivo = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False, default='VENTAS')  # por ahora VENTAS
    descripcion = db.Column(db.String(200), nullable=True)
    meta = db.Column(db.Float, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=True)    # NULL = meta anual
    activa = db.Column(db.Boolean, nullable=False, default=True)
    creado_por = db.Column(db.String(120), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id_objetivo': self.id_objetivo,
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'meta': self.meta,
            'anio': self.anio,
            'mes': self.mes,
            'activa': self.activa,
            'creado_por': self.creado_por,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }
