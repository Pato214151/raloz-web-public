"""
Memoria del negocio: cosas que el dueño le enseña al asistente de IA
para que las recuerde.
"""

from app import db
from datetime import datetime


class MemoriaNegocio(db.Model):
    """Memoria empresarial: decisiones y preferencias del Jefe (no son órdenes
    ejecutables ni datos de la BD, sino contexto persistente).
    Ej: 'Prefiero trabajar con el proveedor X', 'Manyanet es prioridad'."""
    __tablename__ = 'memoria_negocio'

    TIPOS = ('DECISION', 'PREFERENCIA', 'NOTA')

    id_memoria = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False, default='NOTA')
    texto = db.Column(db.String(500), nullable=False)
    activa = db.Column(db.Boolean, nullable=False, default=True)
    creado_por = db.Column(db.String(120), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id_memoria': self.id_memoria,
            'tipo': self.tipo,
            'texto': self.texto,
            'activa': self.activa,
            'creado_por': self.creado_por,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }
