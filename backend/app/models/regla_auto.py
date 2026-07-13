from app import db
from datetime import datetime
import json


class ReglaAuto(db.Model):
    """Regla de automatización toggleable ('si pasa X → haz Y').
    El motor (services/reglas.py, llamado por un daemon) evalúa las activas."""
    __tablename__ = 'reglas_auto'

    clave = db.Column(db.String(50), primary_key=True)   # ej: 'alerta_stock_bajo'
    activa = db.Column(db.Boolean, default=False)
    config = db.Column(db.Text)                           # JSON con parámetros
    ultima_ejecucion = db.Column(db.DateTime)

    def get_config(self):
        try:
            return json.loads(self.config) if self.config else {}
        except (ValueError, TypeError):
            return {}

    def to_dict(self):
        return {
            'clave': self.clave,
            'activa': bool(self.activa),
            'config': self.get_config(),
            'ultima_ejecucion': self.ultima_ejecucion.isoformat() if self.ultima_ejecucion else None,
        }
