"""
Lead: cliente interesado que dejó sus datos (web, WhatsApp o el bot).
"""

from datetime import datetime

from app import db


class Lead(db.Model):
    """Lead / solicitud de cotización capturada desde la tienda web."""
    __tablename__ = 'leads'

    id_lead = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(160))
    telefono = db.Column(db.String(40))
    email = db.Column(db.String(200))
    mensaje = db.Column(db.Text)
    # 'pendiente' | 'contactado' | 'convertido' | 'descartado'
    estado = db.Column(db.String(20), default='pendiente')
    # De dónde vino: 'web' (formulario tienda) | 'whatsapp' | 'otro'
    origen = db.Column(db.String(20), default='web')
    creada = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_lead': self.id_lead,
            'nombre': self.nombre,
            'telefono': self.telefono,
            'email': self.email,
            'mensaje': self.mensaje,
            'estado': self.estado or 'pendiente',
            'origen': self.origen or 'web',
            'creada': self.creada.isoformat() if self.creada else None,
        }
