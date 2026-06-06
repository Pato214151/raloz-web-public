"""
Kardex — libro de movimientos de inventario.

Cada vez que entra mercancía (ENTRADA), se vende (SALIDA) o se corrige
(AJUSTE), queda un registro aquí. Así el stock se puede auditar y los
reportes (entradas vs salidas, balance) salen de un solo lugar.
"""
from datetime import datetime
from app import db


class MovimientoInventario(db.Model):
    __tablename__ = 'movimientos_inventario'

    id = db.Column(db.Integer, primary_key=True)
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    talla_individual = db.Column(db.String(20), nullable=False)

    tipo = db.Column(db.String(20), nullable=False)        # ENTRADA · SALIDA · AJUSTE
    cantidad = db.Column(db.Integer, nullable=False)        # magnitud del movimiento
    stock_resultante = db.Column(db.Integer)               # stock que quedó después

    motivo = db.Column(db.String(200))                     # 'Recepción', 'Venta', 'Ajuste manual'
    referencia = db.Column(db.String(100))                 # ej. número de factura
    usuario = db.Column(db.String(100))
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index('idx_movinv_cps', 'id_colegio', 'id_producto', 'talla_individual'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'id_colegio': self.id_colegio,
            'id_producto': self.id_producto,
            'talla_individual': self.talla_individual,
            'tipo': self.tipo,
            'cantidad': self.cantidad,
            'stock_resultante': self.stock_resultante,
            'motivo': self.motivo,
            'referencia': self.referencia,
            'usuario': self.usuario,
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }
