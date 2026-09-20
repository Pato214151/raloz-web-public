"""
Cliente: datos de contacto y facturación, colegio y estudiante, más totales
acumulados de compras.
"""

from app import db
from datetime import datetime


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id_cliente = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(10), default='CC')
    numero_documento = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(200), nullable=False)
    apellidos = db.Column(db.String(200))
    razon_social = db.Column(db.String(300))
    telefono = db.Column(db.String(50))
    celular = db.Column(db.String(50))
    email = db.Column(db.String(255))
    direccion = db.Column(db.String(500))
    ciudad = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(20))
    pais = db.Column(db.String(50))
    dv = db.Column(db.String(5))
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'))
    estudiante_nombre = db.Column(db.String(200))
    estudiante_grado = db.Column(db.String(50))
    notas = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime)
    total_compras = db.Column(db.Float, default=0)
    total_pagado = db.Column(db.Float, default=0)
    ultima_compra = db.Column(db.Date)
    cantidad_facturas = db.Column(db.Integer, default=0)

    colegio = db.relationship('Colegio', lazy='joined')

    __table_args__ = (
        db.Index('idx_clientes_telefono', 'telefono'),
        db.Index('idx_clientes_documento', 'numero_documento'),
    )

    def to_dict(self):
        return {
            'id_cliente': self.id_cliente,
            'tipo_documento': self.tipo_documento,
            'numero_documento': self.numero_documento,
            'nombre': self.nombre,
            'apellidos': self.apellidos,
            'razon_social': self.razon_social,
            'telefono': self.telefono,
            'celular': self.celular,
            'email': self.email,
            'direccion': self.direccion,
            'ciudad': self.ciudad,
            'departamento': self.departamento,
            'codigo_postal': self.codigo_postal,
            'pais': self.pais,
            'dv': self.dv,
            'id_colegio': self.id_colegio,
            'colegio_nombre': self.colegio.nombre if self.colegio else None,
            'estudiante_nombre': self.estudiante_nombre,
            'estudiante_grado': self.estudiante_grado,
            'notas': self.notas,
            'activo': self.activo,
            'total_compras': self.total_compras or 0,
            'total_pagado': self.total_pagado or 0,
            'ultima_compra': self.ultima_compra.isoformat() if self.ultima_compra else None,
            'cantidad_facturas': self.cantidad_facturas or 0,
        }
