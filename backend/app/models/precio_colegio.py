from app import db


class PrecioColegio(db.Model):
    __tablename__ = 'precios_colegio'

    id_precio = db.Column(db.Integer, primary_key=True)
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla_grupo = db.Column(db.String(50), nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    # Costo unitario para calcular margen/utilidad. NULL = sin costo registrado
    # (el asistente NUNCA inventa costos; si falta, lo dice).
    costo_unitario = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('id_colegio', 'id_producto', 'talla_grupo', name='uq_precio_colegio_producto_talla'),
        db.Index('idx_precios_colegio_producto', 'id_colegio', 'id_producto'),
    )

    def to_dict(self):
        return {
            'id_precio': self.id_precio,
            'id_colegio': self.id_colegio,
            'id_producto': self.id_producto,
            'talla_grupo': self.talla_grupo,
            'precio_unitario': self.precio_unitario,
            'costo_unitario': self.costo_unitario,
        }
