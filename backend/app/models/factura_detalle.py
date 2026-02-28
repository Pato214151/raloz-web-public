from app import db


class FacturaDetalle(db.Model):
    __tablename__ = 'factura_detalle'

    id_detalle = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura', ondelete='CASCADE'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla_individual = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    total_linea = db.Column(db.Float, nullable=False)

    producto = db.relationship('Producto', lazy='joined')

    __table_args__ = (
        db.Index('idx_detalle_factura', 'id_factura'),
    )

    def to_dict(self):
        return {
            'id_detalle': self.id_detalle,
            'id_factura': self.id_factura,
            'id_producto': self.id_producto,
            'producto_nombre': self.producto.nombre if self.producto else None,
            'talla_individual': self.talla_individual,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'total_linea': self.total_linea,
        }
