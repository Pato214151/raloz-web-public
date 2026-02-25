from app import db
from datetime import datetime


class Stock(db.Model):
    __tablename__ = 'stock'

    id_stock = db.Column(db.Integer, primary_key=True)
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla_individual = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Integer, default=0)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('id_colegio', 'id_producto', 'talla_individual', name='uq_stock_colegio_producto_talla'),
        db.Index('idx_stock_colegio_producto', 'id_colegio', 'id_producto'),
    )

    def to_dict(self):
        return {
            'id_stock': self.id_stock,
            'id_colegio': self.id_colegio,
            'id_producto': self.id_producto,
            'talla_individual': self.talla_individual,
            'cantidad': self.cantidad,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }
