"""
El Observador NO debe alertar del stock de colegios inactivos (Adventista, id 2).
"""
from app import db
from app.models import Colegio, Producto, PrecioColegio, Stock
from app.services import event_engine as ee


def test_no_alerta_stock_de_adventista(app):
    with app.app_context():
        db.session.add(Colegio(id_colegio=2, nombre='Adventista'))
        db.session.add(Colegio(id_colegio=3, nombre='Manyanet'))
        db.session.add(Producto(id_producto=1, nombre='Pantalón Diario Niño'))
        db.session.add(PrecioColegio(id_colegio=2, id_producto=1, talla_grupo='M',
                                     precio_unitario=80000))
        db.session.add(PrecioColegio(id_colegio=3, id_producto=1, talla_grupo='M',
                                     precio_unitario=80000))
        db.session.add(Stock(id_colegio=2, id_producto=1, talla_individual='M', cantidad=0))
        db.session.add(Stock(id_colegio=3, id_producto=1, talla_individual='M', cantidad=0))
        db.session.commit()
        cands = ee.detectar_stock()
        colegios = {c['datos'].get('id_colegio') for c in cands}
        assert 3 in colegios          # Manyanet sí alerta
        assert 2 not in colegios      # Adventista NO
