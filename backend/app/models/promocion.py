from app import db
from datetime import datetime


class Promocion(db.Model):
    """Publicación/oferta libre para la portada de la tienda (ej: '2 pares por $X').
    La foto es opcional y se guarda como data URL base64 (sin almacenamiento externo)."""
    __tablename__ = 'promociones'

    id_promocion = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    texto = db.Column(db.Text)
    foto = db.Column(db.Text)                 # data URL base64, opcional
    activa = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_promocion': self.id_promocion,
            'titulo': self.titulo,
            'texto': self.texto,
            'foto': self.foto,
            'activa': bool(self.activa),
            'orden': self.orden or 0,
            'fecha': self.fecha.isoformat() + 'Z' if self.fecha else None,
        }
