"""
Citas que agenda el bot de WhatsApp (nombre, día, hora y colegio).
"""

from datetime import datetime

from app import db


class Cita(db.Model):
    """Solicitud de cita agendada por un cliente desde el bot de WhatsApp."""
    __tablename__ = 'citas'

    id_cita = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(40))
    nombre = db.Column(db.String(160))
    dia = db.Column(db.String(120))
    hora = db.Column(db.String(60))
    colegio = db.Column(db.String(120))
    # 'pendiente' | 'confirmada' | 'atendida' | 'cancelada'
    estado = db.Column(db.String(20), default='pendiente')
    creada = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_cita': self.id_cita,
            'chat_id': self.chat_id,
            'nombre': self.nombre,
            'dia': self.dia,
            'hora': self.hora,
            'colegio': self.colegio,
            'estado': self.estado or 'pendiente',
            'creada': self.creada.isoformat() if self.creada else None,
        }
