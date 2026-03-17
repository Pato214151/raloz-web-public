from app import db
from datetime import datetime


class PedidoFabricacion(db.Model):
    __tablename__ = 'pedidos_fabricacion'

    id_pedido        = db.Column(db.Integer, primary_key=True)
    id_pedido_web    = db.Column(db.Integer, db.ForeignKey('pedidos_web.id_pedido'), nullable=True)

    # Cliente
    nombre_cliente   = db.Column(db.String(200), nullable=False)
    email_cliente    = db.Column(db.String(200))
    telefono_cliente = db.Column(db.String(50))
    id_colegio       = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'))
    nombre_colegio   = db.Column(db.String(200))

    # Montos
    total_orden      = db.Column(db.Float, nullable=False)  # total real del pedido
    abono_porcentaje = db.Column(db.Integer, default=50)    # 50 o 100
    abono_monto      = db.Column(db.Float, nullable=False)  # lo que ya pagó
    saldo_pendiente  = db.Column(db.Float, default=0)       # lo que falta por pagar

    # Items (mismo formato JSON que pedidos_web)
    items_json       = db.Column(db.Text, nullable=False)

    # Estado y fechas
    fecha_pedido     = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_estimada   = db.Column(db.Date, nullable=True)
    estado           = db.Column(db.String(50), default='en_produccion')
    # Estados: en_produccion | listo_para_entrega | entregado

    notificado       = db.Column(db.Boolean, default=False)

    # Relaciones
    colegio          = db.relationship('Colegio', foreign_keys=[id_colegio])

    __table_args__ = (
        db.Index('idx_pfab_estado',    'estado'),
        db.Index('idx_pfab_colegio',   'id_colegio'),
        db.Index('idx_pfab_pedidoweb', 'id_pedido_web'),
    )

    def to_dict(self):
        import json
        return {
            'id_pedido':        self.id_pedido,
            'id_pedido_web':    self.id_pedido_web,
            'nombre_cliente':   self.nombre_cliente,
            'email_cliente':    self.email_cliente,
            'telefono_cliente': self.telefono_cliente,
            'nombre_colegio':   self.nombre_colegio,
            'total_orden':      self.total_orden,
            'abono_porcentaje': self.abono_porcentaje,
            'abono_monto':      self.abono_monto,
            'saldo_pendiente':  self.saldo_pendiente,
            'fecha_pedido':     self.fecha_pedido.isoformat() if self.fecha_pedido else None,
            'fecha_estimada':   self.fecha_estimada.isoformat() if self.fecha_estimada else None,
            'estado':           self.estado,
            'notificado':       self.notificado,
            'items':            json.loads(self.items_json) if self.items_json else [],
        }
