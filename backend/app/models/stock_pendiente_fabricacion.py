"""
Prendas que hay que mandar a fabricar, agrupadas por colegio, producto y talla.
"""

from app import db
from datetime import datetime


class StockPendienteFabricacion(db.Model):
    __tablename__ = 'stock_pendiente_fabricacion'

    id_pendiente      = db.Column(db.Integer, primary_key=True)
    id_colegio        = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto       = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla             = db.Column(db.String(20), nullable=False)
    cantidad_pendiente = db.Column(db.Integer, default=0)
    ids_pedidos       = db.Column(db.Text, default='')   # "101,102,103"
    fecha_creacion    = db.Column(db.DateTime, default=datetime.utcnow)
    estado            = db.Column(db.String(20), default='pendiente')  # pendiente | completado

    # Relaciones
    colegio           = db.relationship('Colegio',  foreign_keys=[id_colegio])
    producto          = db.relationship('Producto', foreign_keys=[id_producto])

    __table_args__ = (
        db.UniqueConstraint('id_colegio', 'id_producto', 'talla', 'estado',
                            name='uq_spf_colegio_prod_talla_estado'),
        db.Index('idx_spf_colegio',  'id_colegio'),
        db.Index('idx_spf_estado',   'estado'),
    )

    def to_dict(self):
        return {
            'id_pendiente':      self.id_pendiente,
            'id_colegio':        self.id_colegio,
            'nombre_colegio':    self.colegio.nombre if self.colegio else '',
            'id_producto':       self.id_producto,
            'nombre_producto':   self.producto.nombre if self.producto else '',
            'talla':             self.talla,
            'cantidad_pendiente': self.cantidad_pendiente,
            'ids_pedidos':       self.ids_pedidos,
            'fecha_creacion':    self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'estado':            self.estado,
        }
