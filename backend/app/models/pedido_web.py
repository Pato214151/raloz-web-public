from app import db
from datetime import datetime


class PedidoWeb(db.Model):
    __tablename__ = 'pedidos_web'

    id_pedido = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(100), unique=True, nullable=False)  # Ref única para Wompi

    # Cliente
    nombre_cliente = db.Column(db.String(200), nullable=False)
    email_cliente = db.Column(db.String(200), nullable=False)
    telefono_cliente = db.Column(db.String(50))
    documento_cliente = db.Column(db.String(50))
    direccion_envio = db.Column(db.String(300), nullable=True)

    # Colegio
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'))
    nombre_colegio = db.Column(db.String(200))

    # Items (JSON: [{id_producto, nombre, talla, cantidad, precio_unitario}])
    items_json = db.Column(db.Text, nullable=False)

    # Totales
    total = db.Column(db.Float, nullable=False)          # monto cobrado ahora (50% o 100%)
    total_orden = db.Column(db.Float)                    # valor real completo del pedido
    abono_porcentaje = db.Column(db.Integer, default=100)
    tiene_fabricacion = db.Column(db.Boolean, default=False)
    tipo_entrega = db.Column(db.String(20), default='completa')
    # Cómo lo recibe el cliente: 'local' (recoge en el punto) o 'envio'.
    # Sin esto no se sabe si empacar para despacho o dejarlo apartado.
    metodo_entrega = db.Column(db.String(20), default='local')

    # Pago
    estado = db.Column(db.String(50), default='pendiente')  # pendiente, pagado, fallido, cancelado
    metodo_pago = db.Column(db.String(100))
    # MEJORA #7: Renombrado de wompi_transaction_id → mp_preference_id
    # (columna renombrada via migración automática en run.py)
    mp_preference_id = db.Column(db.String(200))
    wompi_status = db.Column(db.String(100))

    # Relación con factura (cuando se confirma el pago)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura'), nullable=True)

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_pago = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        import json
        return {
            'id_pedido': self.id_pedido,
            'referencia': self.referencia,
            'nombre_cliente': self.nombre_cliente,
            'email_cliente': self.email_cliente,
            'telefono_cliente': self.telefono_cliente,
            'direccion_envio': self.direccion_envio or '',
            'nombre_colegio': self.nombre_colegio,
            'items': json.loads(self.items_json) if self.items_json else [],
            'total': self.total,
            'total_orden': getattr(self, 'total_orden', self.total),
            'abono_porcentaje': getattr(self, 'abono_porcentaje', 100),
            'tiene_fabricacion': getattr(self, 'tiene_fabricacion', False),
            'tipo_entrega': getattr(self, 'tipo_entrega', 'completa'),
            'metodo_entrega': getattr(self, 'metodo_entrega', None) or 'local',
            'estado': self.estado,
            'metodo_pago': self.metodo_pago,
            'fecha_creacion': (self.fecha_creacion.isoformat() + 'Z') if self.fecha_creacion else None,
            'fecha_pago': (self.fecha_pago.isoformat() + 'Z') if self.fecha_pago else None,
        }
