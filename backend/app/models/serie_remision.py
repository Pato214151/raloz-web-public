"""
Serie de numeración de remisiones.
"""

from app import db


class SerieRemision(db.Model):
    __tablename__ = 'series_remision'

    id_serie = db.Column(db.Integer, primary_key=True)
    prefijo = db.Column(db.String(10), default='R')
    ano = db.Column(db.Integer)
    consecutivo_actual = db.Column(db.Integer, default=0)
    activa = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id_serie': self.id_serie,
            'prefijo': self.prefijo,
            'ano': self.ano,
            'consecutivo_actual': self.consecutivo_actual,
            'activa': self.activa,
        }
