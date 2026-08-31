from app import db
from datetime import datetime
import json


class AccionAsistente(db.Model):
    """Bitácora de acciones ejecutadas por el Asistente (Action Journal).

    Guarda el estado ANTES y DESPUÉS de cada escritura para poder:
      - verificar contra la fuente de verdad que el cambio quedó, y
      - revertir (rollback) la acción restaurando el estado anterior.
    """
    __tablename__ = 'acciones_asistente'

    id_accion = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(40), nullable=False)          # ajustar_stock, fijar_costo, ...
    descripcion = db.Column(db.String(400), nullable=True)    # legible para el humano
    estado_antes = db.Column(db.Text, nullable=True)          # JSON con lo necesario para revertir
    estado_despues = db.Column(db.Text, nullable=True)        # JSON con el resultado esperado
    reversible = db.Column(db.Boolean, default=False, nullable=False)
    verificado = db.Column(db.Boolean, default=False, nullable=False)
    # EJECUTADA · VERIFICADA · FALLO_VERIFICACION · REVERTIDA · FALLO_REVERSION
    resultado = db.Column(db.String(30), default='EJECUTADA', nullable=False)
    # Si esta fila es una reversión, apunta a la acción original que revierte
    reversion_de = db.Column(db.Integer, db.ForeignKey('acciones_asistente.id_accion'), nullable=True)
    usuario = db.Column(db.String(120), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_antes(self, obj):
        self.estado_antes = json.dumps(obj, ensure_ascii=False, default=str)

    def set_despues(self, obj):
        self.estado_despues = json.dumps(obj, ensure_ascii=False, default=str)

    @property
    def antes(self):
        try:
            return json.loads(self.estado_antes) if self.estado_antes else None
        except Exception:
            return None

    @property
    def despues(self):
        try:
            return json.loads(self.estado_despues) if self.estado_despues else None
        except Exception:
            return None

    def to_dict(self):
        return {
            'id_accion': self.id_accion,
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'reversible': self.reversible,
            'verificado': self.verificado,
            'resultado': self.resultado,
            'reversion_de': self.reversion_de,
            'usuario': self.usuario,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }
