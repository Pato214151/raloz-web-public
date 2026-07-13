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
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

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
        }
