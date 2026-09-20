"""
Producto (prenda): código, nombre, tipo y si se publica en la tienda
(con ventana de fechas).
"""

from app import db
from datetime import datetime


class Producto(db.Model):
    __tablename__ = 'productos'

    id_producto = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)
    destacado = db.Column(db.Boolean, default=False)   # aparece en "Productos destacados"
    orden = db.Column(db.Integer, default=0)           # orden de aparición en la tienda
    publicar_desde = db.Column(db.DateTime)            # programación: visible a partir de (UTC)
    publicar_hasta = db.Column(db.DateTime)            # programación: se oculta después de (UTC)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def en_ventana(self, ahora=None):
        """True si el producto está dentro de su ventana de publicación programada
        (o no tiene ventana). No considera el flag `activo`."""
        ahora = ahora or datetime.utcnow()
        if self.publicar_desde and ahora < self.publicar_desde:
            return False
        if self.publicar_hasta and ahora > self.publicar_hasta:
            return False
        return True

    precios = db.relationship('PrecioColegio', backref='producto', lazy='dynamic')
    stocks = db.relationship('Stock', backref='producto', lazy='dynamic')

    def to_dict(self):
        return {
            'id_producto': self.id_producto,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'tipo': self.tipo,
            'activo': self.activo,
            'destacado': bool(self.destacado),
            'orden': self.orden or 0,
            'publicar_desde': self.publicar_desde.isoformat() if self.publicar_desde else None,
            'publicar_hasta': self.publicar_hasta.isoformat() if self.publicar_hasta else None,
        }
