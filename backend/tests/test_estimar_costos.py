"""
Costos estimados (placeholder mientras se consiguen los reales).
"""
from app import db
from app.models import PrecioColegio, ConfigSitio
from app.api.asistente import _aplicar_costos_estimados


def test_rellena_solo_faltantes_al_60(app):
    with app.app_context():
        # una sin costo, otra con costo real ya cargado
        db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='M',
                                     precio_unitario=40000, costo_unitario=None))
        db.session.add(PrecioColegio(id_colegio=1, id_producto=2, talla_grupo='M',
                                     precio_unitario=50000, costo_unitario=30000))
        db.session.commit()
        n, factor = _aplicar_costos_estimados(0.6, solo_faltantes=True)
        assert n == 1 and factor == 0.6
        # la que faltaba quedó en 40000*0.6 = 24000
        r1 = PrecioColegio.query.filter_by(id_producto=1).first()
        assert r1.costo_unitario == 24000
        # la real NO se pisó
        r2 = PrecioColegio.query.filter_by(id_producto=2).first()
        assert r2.costo_unitario == 30000
        # quedó marcada la bandera de estimados
        assert ConfigSitio.get('costos_estimados') == '1'
        assert ConfigSitio.get('costos_factor') == '0.6'
