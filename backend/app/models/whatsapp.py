from datetime import datetime

from app import db


class WaConversacion(db.Model):
    """Una conversación de WhatsApp con un cliente (identificada por su chat_id/wa_id)."""
    __tablename__ = 'wa_conversaciones'

    chat_id = db.Column(db.String(40), primary_key=True)
    nombre = db.Column(db.String(160))
    ultimo_mensaje = db.Column(db.Text)
    ultima_fecha = db.Column(db.DateTime, default=datetime.utcnow)
    no_leidos = db.Column(db.Integer, default=0)
    # 'bot' = el bot responde solo · 'humano' = un asesor tomó el chat (bot en silencio)
    modo = db.Column(db.String(10), default='bot')

    def to_dict(self):
        return {
            'chat_id': self.chat_id,
            'nombre': self.nombre,
            'ultimo_mensaje': self.ultimo_mensaje,
            'ultima_fecha': self.ultima_fecha.isoformat() if self.ultima_fecha else None,
            'no_leidos': self.no_leidos or 0,
            'modo': self.modo or 'bot',
        }


class WaMensaje(db.Model):
    """Un mensaje individual de una conversación (entrante o saliente)."""
    __tablename__ = 'wa_mensajes'

    id_mensaje = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(40), nullable=False, index=True)
    direccion = db.Column(db.String(4), nullable=False)   # 'in' | 'out'
    texto = db.Column(db.Text)
    autor = db.Column(db.String(120))                     # 'cliente' | 'bot' | nombre del asesor
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    # Adjuntos: 'image' | 'document' | 'audio'... y el archivo en base64.
    # Por rendimiento, to_dict NO devuelve el base64 (se pide aparte por su endpoint).
    media_tipo = db.Column(db.String(20))
    media_b64 = db.Column(db.Text)

    def to_dict(self):
        return {
            'id_mensaje': self.id_mensaje,
            'chat_id': self.chat_id,
            'direccion': self.direccion,
            'texto': self.texto,
            'autor': self.autor,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'media_tipo': self.media_tipo,
            'tiene_media': bool(self.media_b64),
        }
