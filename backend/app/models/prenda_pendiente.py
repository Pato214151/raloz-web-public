"""
Prenda que se vendió pero quedó pendiente de entregar.
"""

from app import db
from datetime import date


class PrendaPendiente(db.Model):
    __tablename__ = 'prendas_pendientes'

    id_pendiente = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura'), nullable=False)
    numero_factura = db.Column(db.String(50))
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    colegio_nombre = db.Column(db.String(200))
    cliente_nombre = db.Column(db.String(200))
    producto_nombre = db.Column(db.String(200), nullable=False)
    talla = db.Column(db.String(20))
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    genero = db.Column(db.String(20), default='NIÑO')
    estado = db.Column(db.String(20), default='PENDIENTE')
    fecha_registro = db.Column(db.Date, default=date.today)
    fecha_entrega = db.Column(db.Date)
    fecha_factura = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    usuario_registro = db.Column(db.String(100))

    __table_args__ = (
        db.Index('idx_prendas_estado', 'estado'),
        db.Index('idx_prendas_factura', 'id_factura'),
        db.Index('idx_prendas_colegio', 'id_colegio'),
    )

    def to_dict(self):
        return {
            'id_pendiente': self.id_pendiente,
            'id_factura': self.id_factura,
            'numero_factura': self.numero_factura,
            'id_colegio': self.id_colegio,
            'colegio_nombre': self.colegio_nombre,
            'cliente_nombre': self.cliente_nombre,
            'producto_nombre': self.producto_nombre,
            'talla': self.talla,
            'cantidad': self.cantidad,
            'genero': self.genero,
            'estado': self.estado,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'fecha_entrega': self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            'fecha_factura': self.fecha_factura.isoformat() if self.fecha_factura else None,
            'observaciones': self.observaciones,
            'usuario_registro': self.usuario_registro,
        }
