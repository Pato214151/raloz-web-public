from app import db


class MetodoPago(db.Model):
    __tablename__ = 'metodos_pago'

    id_metodo = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id_metodo': self.id_metodo,
            'nombre': self.nombre,
            'activo': self.activo,
        }
