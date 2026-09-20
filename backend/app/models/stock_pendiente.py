"""
Faltante de stock detectado al facturar: lo que se vendió y no había.
"""

from app import db
from datetime import date


class StockPendiente(db.Model):
    __tablename__ = 'stock_pendiente'

    id_pendiente = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura'), nullable=False)
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla_individual = db.Column(db.String(20), nullable=False)
    cantidad_faltante = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='PENDIENTE')
    fecha_registro = db.Column(db.Date, default=date.today)

    factura = db.relationship('Factura', lazy='joined', back_populates='pendientes')
    colegio = db.relationship('Colegio', lazy='joined')
    producto = db.relationship('Producto', lazy='joined')

    __table_args__ = (
        db.Index('idx_pendientes_factura', 'id_factura'),
        db.Index('idx_pendientes_estado', 'estado'),
    )

    def to_dict(self):
        return {
            'id_pendiente': self.id_pendiente,
            'id_factura': self.id_factura,
            'numero_factura': self.factura.numero_factura if self.factura else None,
            'id_colegio': self.id_colegio,
            'colegio_nombre': self.colegio.nombre if self.colegio else None,
            'id_producto': self.id_producto,
            'producto_nombre': self.producto.nombre if self.producto else None,
            'talla_individual': self.talla_individual,
            'cantidad_faltante': self.cantidad_faltante,
            'estado': self.estado,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
        }
