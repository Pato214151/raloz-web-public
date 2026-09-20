"""
Suscripción del navegador para enviar notificaciones push al equipo.
"""

from app import db
from datetime import datetime


class PushSubscription(db.Model):
    """Suscripción de Web Push de un navegador/dispositivo del panel.
    Guarda los datos que entrega el navegador (endpoint + llaves) para poder
    enviarle notificaciones (ej: 'nuevo mensaje de WhatsApp')."""
    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.Text, unique=True, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    usuario = db.Column(db.String(80))              # quién la registró (informativo)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_webpush(self):
        return {'endpoint': self.endpoint, 'keys': {'p256dh': self.p256dh, 'auth': self.auth}}
