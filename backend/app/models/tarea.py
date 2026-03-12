from app import db
from datetime import datetime


class Tarea(db.Model):
    __tablename__ = 'tareas'

    id_tarea = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    prioridad = db.Column(db.String(10), default='MEDIA', nullable=True)  # ALTA, MEDIA, BAJA
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    # NULL = para todos los vendedores; un id = asignada a ese usuario
    asignada_a = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=True)
    creada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    completada = db.Column(db.Boolean, default=False)
    completada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=True)
    fecha_completada = db.Column(db.DateTime, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    asignado = db.relationship('Usuario', foreign_keys=[asignada_a], backref='tareas_asignadas')
    creador = db.relationship('Usuario', foreign_keys=[creada_por], backref='tareas_creadas')
    completador = db.relationship('Usuario', foreign_keys=[completada_por], backref='tareas_completadas')

    def to_dict(self):
        return {
            'id_tarea': self.id_tarea,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'prioridad': self.prioridad or 'MEDIA',
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'asignada_a': self.asignada_a,
            'asignada_a_nombre': self.asignado.usuario if self.asignado else None,
            'creada_por': self.creada_por,
            'creada_por_nombre': self.creador.usuario if self.creador else None,
            'completada': self.completada,
            'completada_por_nombre': self.completador.usuario if self.completador else None,
            'fecha_completada': self.fecha_completada.isoformat() if self.fecha_completada else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }
