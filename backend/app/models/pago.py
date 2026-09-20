"""
Pago o abono aplicado a una factura.
"""

from app import db
from datetime import datetime


class Pago(db.Model):
    __tablename__ = 'pagos'

    id_pago = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura', ondelete='CASCADE'), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    usuario_registro = db.Column(db.String(100), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_pagos_factura', 'id_factura'),
    )

    def to_dict(self):
        return {
            'id_pago': self.id_pago,
            'id_factura': self.id_factura,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'valor': self.valor,
            'metodo_pago': self.metodo_pago,
            'usuario_registro': self.usuario_registro,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
        }
