from app import db
from datetime import datetime


class Colegio(db.Model):
    __tablename__ = 'colegios'

    id_colegio = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), unique=True, nullable=False)
    ciudad = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    precios = db.relationship('PrecioColegio', backref='colegio', lazy='dynamic')
    stocks = db.relationship('Stock', backref='colegio', lazy='dynamic')
    facturas = db.relationship('Factura', backref='colegio', lazy='dynamic')

    def to_dict(self):
        return {
            'id_colegio': self.id_colegio,
            'nombre': self.nombre,
            'ciudad': self.ciudad,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }
