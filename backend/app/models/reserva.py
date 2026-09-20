"""
Reserva temporal de stock mientras un cliente termina de pagar en la tienda.
Si no paga, expira y el stock se libera.
"""

from app import db
from datetime import datetime


class Reserva(db.Model):
    __tablename__ = 'reservas'

    id_reserva       = db.Column(db.Integer, primary_key=True)
    session_id       = db.Column(db.String(100), nullable=False)
    id_colegio       = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto      = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla            = db.Column(db.String(20), nullable=False)
    cantidad         = db.Column(db.Integer, nullable=False, default=1)
    fecha_creacion   = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)
    estado           = db.Column(db.String(20), default='activa')  # activa | completada | cancelada | expirada

    __table_args__ = (
        db.Index('idx_reservas_sesion',    'session_id'),
        db.Index('idx_reservas_stock',     'id_colegio', 'id_producto', 'talla'),
        db.Index('idx_reservas_estado_exp','estado', 'fecha_expiracion'),
    )

    def to_dict(self):
        return {
            'id_reserva':       self.id_reserva,
            'session_id':       self.session_id,
            'id_colegio':       self.id_colegio,
            'id_producto':      self.id_producto,
            'talla':            self.talla,
            'cantidad':         self.cantidad,
            'fecha_expiracion': self.fecha_expiracion.isoformat(),
            'estado':           self.estado,
        }
