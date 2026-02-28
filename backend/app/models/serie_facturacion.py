from app import db


class SerieFacturacion(db.Model):
    __tablename__ = 'series_facturacion'

    id_serie = db.Column(db.Integer, primary_key=True)
    prefijo = db.Column(db.String(10), default='FAC')
    ano = db.Column(db.Integer)
    consecutivo_actual = db.Column(db.Integer, default=0)
    formato = db.Column(db.String(100), default='FAC-{ano}-{consecutivo:06d}')
    activa = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id_serie': self.id_serie,
            'prefijo': self.prefijo,
            'ano': self.ano,
            'consecutivo_actual': self.consecutivo_actual,
            'formato': self.formato,
            'activa': self.activa,
        }
