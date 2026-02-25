from app import db
from datetime import datetime


class CajaDiaria(db.Model):
    __tablename__ = 'caja_diaria'

    id_caja = db.Column(db.Integer, primary_key=True)
    fecha_apertura = db.Column(db.DateTime, nullable=False)
    fecha_cierre = db.Column(db.DateTime)
    usuario_apertura = db.Column(db.String(100), nullable=False)
    usuario_cierre = db.Column(db.String(100))
    monto_inicial = db.Column(db.Float, default=0)
    total_ventas = db.Column(db.Float, default=0)
    total_gastos = db.Column(db.Float, default=0)
    monto_esperado = db.Column(db.Float, default=0)
    monto_real = db.Column(db.Float, default=0)
    diferencia = db.Column(db.Float, default=0)
    estado = db.Column(db.String(20), default='ABIERTA')
    observaciones = db.Column(db.Text)

    movimientos = db.relationship('MovimientoCaja', backref='caja', lazy='dynamic')

    def to_dict(self):
        return {
            'id_caja': self.id_caja,
            'fecha_apertura': self.fecha_apertura.isoformat() if self.fecha_apertura else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'usuario_apertura': self.usuario_apertura,
            'usuario_cierre': self.usuario_cierre,
            'monto_inicial': self.monto_inicial,
            'total_ventas': self.total_ventas,
            'total_gastos': self.total_gastos,
            'monto_esperado': self.monto_esperado,
            'monto_real': self.monto_real,
            'diferencia': self.diferencia,
            'estado': self.estado,
            'observaciones': self.observaciones,
        }
