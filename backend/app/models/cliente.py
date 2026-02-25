from app import db
from datetime import datetime


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id_cliente = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(10), default='CC')
    numero_documento = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(50))
    email = db.Column(db.String(255))
    direccion = db.Column(db.String(500))
    id_colegio = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'))
    notas = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

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
            'telefono': self.telefono,
            'email': self.email,
            'direccion': self.direccion,
            'id_colegio': self.id_colegio,
            'colegio_nombre': self.colegio.nombre if self.colegio else None,
            'notas': self.notas,
            'activo': self.activo,
        }
