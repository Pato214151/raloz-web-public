from app import db
from datetime import datetime


class Factura(db.Model):
    __tablename__ = 'facturas'

    id_factura = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), unique=True, nullable=False)
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=False)
    cliente_nombre = db.Column(db.String(200))
    cliente_telefono = db.Column(db.String(50))
    cliente_email = db.Column(db.String(255))
    cliente_direccion = db.Column(db.String(500))
    cliente_nit = db.Column(db.String(50))
    fecha_factura = db.Column(db.Date, nullable=False)
    total = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float)
    total_abonado = db.Column(db.Float, default=0)
    saldo_pendiente = db.Column(db.Float, default=0)
    estado = db.Column(db.String(20), default='PENDIENTE')
    estado_entrega = db.Column(db.String(20), default='POR_ENTREGAR')
    metodo_pago = db.Column(db.String(50))
    genero_estudiante = db.Column(db.String(20))
    domicilio = db.Column(db.Float, default=0)
    canal = db.Column(db.String(20), default='PRESENCIAL')  # 'PRESENCIAL' o 'WEB'
    mp_saldo_payment_id = db.Column(db.String(50))  # id del pago MP que saldó el saldo (idempotencia)
    observaciones = db.Column(db.Text)
    fecha_entrega = db.Column(db.Date)
    usuario_creacion = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    detalles = db.relationship('FacturaDetalle', backref='factura', lazy='dynamic', cascade='all, delete-orphan')
    pagos = db.relationship('Pago', backref='factura', lazy='dynamic', cascade='all, delete-orphan')
    pendientes = db.relationship('StockPendiente', back_populates='factura', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_facturas_numero', 'numero_factura'),
        db.Index('idx_facturas_cliente_nombre', 'cliente_nombre'),
        db.Index('idx_facturas_estado', 'estado'),
        db.Index('idx_facturas_fecha', 'fecha_factura'),
        db.Index('idx_facturas_colegio', 'id_colegio'),
        db.Index('idx_facturas_saldo', 'saldo_pendiente'),
    )

    def recalcular_desde_pagos(self):
        """Recalcula total_abonado, saldo_pendiente y estado a partir de los
        pagos registrados. Única fuente de esa regla (la usan pagos y facturas).
        No toca facturas ANULADAS. No hace commit."""
        total_pagado = sum(p.valor for p in self.pagos)
        self.total_abonado = total_pagado
        self.saldo_pendiente = max((self.total or 0) - total_pagado, 0)
        if self.estado == 'ANULADA':
            return
        self.estado = 'PAGADA' if total_pagado >= (self.total or 0) else 'PENDIENTE'

    def to_dict(self):
        return {
            'id_factura': self.id_factura,
            'numero_factura': self.numero_factura,
            'id_colegio': self.id_colegio,
            'colegio_nombre': self.colegio.nombre if self.colegio else None,
            'cliente_nombre': self.cliente_nombre,
            'cliente_telefono': self.cliente_telefono,
            'cliente_email': self.cliente_email,
            'cliente_nit': self.cliente_nit,
            'fecha_factura': self.fecha_factura.isoformat() if self.fecha_factura else None,
            'total': self.total,
            'subtotal': self.subtotal,
            'total_abonado': self.total_abonado or 0,
            'saldo_pendiente': self.saldo_pendiente or 0,
            'estado': self.estado,
            'estado_entrega': self.estado_entrega,
            'metodo_pago': self.metodo_pago,
            'genero_estudiante': self.genero_estudiante,
            'domicilio': self.domicilio or 0,
            'canal': self.canal or 'PRESENCIAL',
            'observaciones': self.observaciones,
            'fecha_entrega': self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            'usuario_creacion': self.usuario_creacion,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }

    def to_dict_full(self):
        data = self.to_dict()
        data['detalles'] = [d.to_dict() for d in self.detalles]
        data['pagos'] = [p.to_dict() for p in self.pagos]
        data['total_pagado'] = sum(p.valor for p in self.pagos)
        data['saldo'] = self.total - data['total_pagado']
        return data
