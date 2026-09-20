"""
Eventos que detecta el sistema (stock bajo, ventas raras, pagos sin
confirmar...). Tienen severidad, recomendación y clave para no repetirse.
"""

from app import db
from datetime import datetime
import json


class Evento(db.Model):
    """Señal del negocio detectada por el Event Engine (sistema nervioso).

    El Observador escanea la operación (stock, cartera, pedidos, ventas) y
    registra aquí lo relevante, priorizado por severidad. `clave_dedup` evita
    que el mismo hecho se repita como ruido en cada escaneo.
    """
    __tablename__ = 'eventos'

    # Severidades (de mayor a menor prioridad)
    CRITICO = 'CRITICO'          # 🔴
    IMPORTANTE = 'IMPORTANTE'    # 🟠
    PRECAUCION = 'PRECAUCION'    # 🟡
    INFORMATIVO = 'INFORMATIVO'  # 🔵

    id_evento = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)          # stock_agotado, factura_por_cobrar, ...
    severidad = db.Column(db.String(15), nullable=False, default=INFORMATIVO)
    titulo = db.Column(db.String(200), nullable=False)
    detalle = db.Column(db.String(500), nullable=True)
    entidad_tipo = db.Column(db.String(30), nullable=True)   # stock · factura · pedido_fabricacion
    entidad_id = db.Column(db.Integer, nullable=True)
    datos = db.Column(db.Text, nullable=True)                # JSON con contexto (análisis, acción sugerida)
    score = db.Column(db.Integer, nullable=True)             # 0-100: impacto+urgencia+probabilidad
    recomendacion = db.Column(db.String(500), nullable=True) # qué recomienda hacer RALOZ
    clave_dedup = db.Column(db.String(160), index=True, nullable=False)
    estado = db.Column(db.String(15), nullable=False, default='NUEVO')  # NUEVO · VISTO · RESUELTO
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    visto_en = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('idx_eventos_estado_sev', 'estado', 'severidad'),
    )

    def set_datos(self, obj):
        self.datos = json.dumps(obj, ensure_ascii=False, default=str) if obj is not None else None

    @property
    def datos_dict(self):
        try:
            return json.loads(self.datos) if self.datos else None
        except Exception:
            return None

    def to_dict(self):
        return {
            'id_evento': self.id_evento,
            'tipo': self.tipo,
            'severidad': self.severidad,
            'titulo': self.titulo,
            'detalle': self.detalle,
            'entidad_tipo': self.entidad_tipo,
            'entidad_id': self.entidad_id,
            'datos': self.datos_dict,
            'score': self.score,
            'recomendacion': self.recomendacion,
            'estado': self.estado,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'visto_en': self.visto_en.isoformat() if self.visto_en else None,
        }
