from app import db
from datetime import datetime


class MovimientoCaja(db.Model):
    __tablename__ = 'movimientos_caja'

    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_caja = db.Column(db.Integer, db.ForeignKey('caja_diaria.id_caja'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    concepto = db.Column(db.String(500))
    valor = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50))
    referencia = db.Column(db.String(200))
    usuario = db.Column(db.String(100), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_movimientos_caja', 'id_caja'),
    )

    def to_dict(self):
        return {
            'id_movimiento': self.id_movimiento,
            'id_caja': self.id_caja,
            'tipo': self.tipo,
            'concepto': self.concepto,
            'valor': self.valor,
            'metodo_pago': self.metodo_pago,
            'referencia': self.referencia,
            'usuario': self.usuario,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None,
        }
