"""
Orden de producción para un taller: prenda, tallas, insumos, logo y costos.
Se imprime en PDF.
"""

from app import db
from datetime import datetime
import json


class OrdenProduccion(db.Model):
    """
    Orden de producción / confección que se manda al taller.
    Describe QUÉ prenda fabricar, con qué INSUMOS (tela, malla, etc.),
    en qué TALLAS y cantidades, y con qué LOGO. Se imprime a PDF.

    insumos_json: [{insumo, especificacion, cantidad, unidad, observacion}, ...]
    tallas_json:  [{talla, cantidad}, ...]
    """
    __tablename__ = 'ordenes_produccion'

    id_orden       = db.Column(db.Integer, primary_key=True)
    numero         = db.Column(db.Integer, nullable=False)  # consecutivo visible (ORD-0001)

    # Cabecera
    prenda         = db.Column(db.String(200), nullable=False)
    id_colegio     = db.Column(db.Integer, db.ForeignKey('colegios.id_colegio'), nullable=True)
    nombre_colegio = db.Column(db.String(200))
    taller         = db.Column(db.String(200))
    fecha          = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_entrega  = db.Column(db.Date, nullable=True)

    # Detalle (JSON)
    insumos_json   = db.Column(db.Text)   # lista de insumos
    tallas_json    = db.Column(db.Text)   # lista de tallas/cantidades

    # Logo
    logo_descripcion = db.Column(db.String(200))
    logo_ubicacion   = db.Column(db.String(120))
    logo_tecnica     = db.Column(db.String(80))   # bordado / estampado / sublimado
    logo_tamano      = db.Column(db.String(60))

    observaciones  = db.Column(db.Text)

    # Costos (opcional)
    costo_tela     = db.Column(db.Float, default=0)
    costo_insumos  = db.Column(db.Float, default=0)
    costo_mano_obra = db.Column(db.Float, default=0)

    estado         = db.Column(db.String(30), default='creada')  # creada | enviada | recibida
    usuario_creacion = db.Column(db.String(120))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    colegio        = db.relationship('Colegio', foreign_keys=[id_colegio])

    __table_args__ = (
        db.Index('idx_ordprod_fecha', 'fecha'),
        db.Index('idx_ordprod_colegio', 'id_colegio'),
    )

    @property
    def numero_fmt(self):
        return f"ORD-{self.numero:04d}"

    @property
    def costo_total(self):
        return (self.costo_tela or 0) + (self.costo_insumos or 0) + (self.costo_mano_obra or 0)

    @property
    def total_prendas(self):
        try:
            return sum(int(t.get('cantidad') or 0) for t in json.loads(self.tallas_json or '[]'))
        except Exception:
            return 0

    def to_dict(self):
        return {
            'id_orden':       self.id_orden,
            'numero':         self.numero,
            'numero_fmt':     self.numero_fmt,
            'prenda':         self.prenda,
            'id_colegio':     self.id_colegio,
            'nombre_colegio': self.nombre_colegio,
            'taller':         self.taller,
            'fecha':          self.fecha.isoformat() if self.fecha else None,
            'fecha_entrega':  self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            'insumos':        json.loads(self.insumos_json) if self.insumos_json else [],
            'tallas':         json.loads(self.tallas_json) if self.tallas_json else [],
            'logo_descripcion': self.logo_descripcion or '',
            'logo_ubicacion': self.logo_ubicacion or '',
            'logo_tecnica':   self.logo_tecnica or '',
            'logo_tamano':    self.logo_tamano or '',
            'observaciones':  self.observaciones or '',
            'costo_tela':     self.costo_tela or 0,
            'costo_insumos':  self.costo_insumos or 0,
            'costo_mano_obra': self.costo_mano_obra or 0,
            'costo_total':    self.costo_total,
            'total_prendas':  self.total_prendas,
            'estado':         self.estado,
            'usuario_creacion': self.usuario_creacion or '',
            'created_at':     self.created_at.isoformat() if self.created_at else None,
        }
