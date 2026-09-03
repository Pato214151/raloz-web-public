"""
Rentabilidad — la utilidad real descuenta el costo de la mercancía vendida (CMV).

Blinda el bug histórico: la utilidad se calculaba como "cobrado − gastos" e
ignoraba lo que costó la prenda, mostrando una utilidad inflada.
"""
from datetime import date

from app import db
from app.models import Factura, FacturaDetalle, PrecioColegio, Producto, Colegio
from app.services.rentabilidad import cmv_periodo, COSTO_PCT_ESTIMADO


def _venta(precio, costo, talla_grupo='S-M', talla_ind='M', cantidad=2):
    db.session.add(Colegio(id_colegio=1, nombre='Manyanet'))
    db.session.add(Producto(id_producto=1, nombre='Blusa'))
    db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo=talla_grupo,
                                 precio_unitario=precio, costo_unitario=costo))
    f = Factura(numero_factura='V1', id_colegio=1, fecha_factura=date.today(),
                total=precio * cantidad, saldo_pendiente=0, estado='PAGADA',
                canal='PRESENCIAL', usuario_creacion='t')
    db.session.add(f)
    db.session.commit()
    db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1,
                                  talla_individual=talla_ind, cantidad=cantidad,
                                  precio_unitario=precio, total_linea=precio * cantidad))
    db.session.commit()


def test_cmv_usa_costo_real_cuando_existe(app):
    with app.app_context():
        _venta(precio=40000, costo=25000, cantidad=2)
        r = cmv_periodo(date.today(), date.today())
        assert r['cmv_total'] == 50000       # 25.000 × 2
        assert r['cmv_real'] == 50000
        assert r['hay_estimado'] is False


def test_cmv_estima_60pct_sin_costo(app):
    with app.app_context():
        _venta(precio=40000, costo=None, cantidad=2)
        r = cmv_periodo(date.today(), date.today())
        # 60% del precio de venta (80.000 vendido → 48.000 de costo estimado)
        assert r['cmv_total'] == round(COSTO_PCT_ESTIMADO * 80000, 2)
        assert r['hay_estimado'] is True


def test_utilidad_bruta_descuenta_cmv(app):
    with app.app_context():
        _venta(precio=40000, costo=25000, cantidad=2)   # vende 80.000, cuesta 50.000
        r = cmv_periodo(date.today(), date.today())
        ventas = 80000
        utilidad_bruta = ventas - r['cmv_total']
        assert utilidad_bruta == 30000                  # NO 80.000
