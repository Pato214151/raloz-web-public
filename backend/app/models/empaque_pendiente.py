from app import db


class EmpaquePendiente(db.Model):
    __tablename__ = 'empaque_pendientes'

    id_empaque = db.Column(db.Integer, primary_key=True)
    id_pendiente = db.Column(db.Integer, db.ForeignKey('prendas_pendientes.id_pendiente'), nullable=False)
    empacado = db.Column(db.Boolean, default=False)
    fecha_empaque = db.Column(db.DateTime)
    usuario_empaque = db.Column(db.String(100))

    prenda = db.relationship('PrendaPendiente', lazy='joined', backref='empaque')

    def to_dict(self):
        return {
            'id_empaque': self.id_empaque,
            'id_pendiente': self.id_pendiente,
            'empacado': self.empacado,
            'fecha_empaque': self.fecha_empaque.isoformat() if self.fecha_empaque else None,
            'usuario_empaque': self.usuario_empaque,
        }
