from app import db
from datetime import datetime
import json


class ReglaNegocio(db.Model):
    """Política persistente del negocio (Business Rules).

    A diferencia de una charla, una regla vive en la BD y RALOZ la respeta:
    'no vender por debajo de $45.000', 'no comprar más de $10M/mes sin aprobar'.
    `parametros` guarda la parte MÁQUINA-verificable (ej. limite/periodo);
    `texto` es la versión humana que se le muestra al modelo.
    """
    __tablename__ = 'reglas_negocio'

    # Categorías conocidas (informativo; se acepta cualquiera)
    CATEGORIAS = ('PRECIO', 'INVENTARIO', 'COMPRAS', 'PROVEEDORES', 'HORARIOS',
                  'PAGOS', 'PROMOCIONES', 'WHATSAPP', 'PUBLICIDAD', 'AUTONOMIA', 'OTRA')

    id_regla = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(20), nullable=False, default='OTRA')
    texto = db.Column(db.String(400), nullable=False)
    parametros = db.Column(db.Text, nullable=True)   # JSON: {"limite":10000000,"periodo":"mensual"}
    activa = db.Column(db.Boolean, nullable=False, default=True)
    creado_por = db.Column(db.String(120), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_parametros(self, obj):
        self.parametros = json.dumps(obj, ensure_ascii=False) if obj else None

    @property
    def params(self):
        try:
            return json.loads(self.parametros) if self.parametros else {}
        except Exception:
            return {}

    def to_dict(self):
        return {
            'id_regla': self.id_regla,
            'categoria': self.categoria,
            'texto': self.texto,
            'parametros': self.params,
            'activa': self.activa,
            'creado_por': self.creado_por,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }
