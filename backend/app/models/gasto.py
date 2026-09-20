"""
Gasto del negocio: valor, categoría, si ya se pagó y con qué método.
"""

from app import db
from datetime import datetime


class Gasto(db.Model):
    __tablename__ = 'gastos'

    id_gasto = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    categoria = db.Column(db.String(100), default='Otros')
    tipo_gasto = db.Column(db.String(20), default='TIENDA')  # 'TIENDA' o 'EMPRESA'
    # 'PAGADO' = gasto real (cuenta en el balance) | 'PENDIENTE' = deuda (no cuenta
    # hasta que se marca pagada, ahí se convierte en gasto del día de pago).
    estado_pago = db.Column(db.String(20), default='PAGADO')
    fecha_pago = db.Column(db.Date, nullable=True)
    usuario_registro = db.Column(db.String(100), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_gastos_fecha', 'fecha'),
    )

    def to_dict(self):
        return {
            'id_gasto': self.id_gasto,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'descripcion': self.descripcion,
            'valor': self.valor,
            'metodo_pago': self.metodo_pago,
            'categoria': self.categoria or 'Otros',
            'tipo_gasto': self.tipo_gasto or 'TIENDA',
            'estado_pago': self.estado_pago or 'PAGADO',
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'usuario_registro': self.usuario_registro,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
        }
