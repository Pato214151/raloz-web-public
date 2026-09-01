"""
Event Engine (sistema nervioso del Observador): detectores + dedup + observar.
"""
from datetime import date, timedelta

from app import db
from app.models import (
    Stock, PrecioColegio, Producto, Colegio, Factura, FacturaDetalle, Evento,
)
from app.services import event_engine as ee


def _base(app):
    """Colegio + producto + precio (para que la prenda sea 'vendible')."""
    with app.app_context():
        db.session.add(Colegio(id_colegio=1, nombre='Manyanet'))
        db.session.add(Producto(id_producto=1, nombre='Blusa Niña'))
        db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='M',
                                     precio_unitario=40000, costo_unitario=25000))
        db.session.commit()


def test_detecta_stock_agotado_y_bajo(app):
    _base(app)
    with app.app_context():
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=0))
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='S', cantidad=2))
        db.session.commit()
        cands = ee.detectar_stock()
        tipos = {c['tipo'] for c in cands}
        assert 'stock_agotado' in tipos and 'stock_bajo' in tipos
        agot = next(c for c in cands if c['tipo'] == 'stock_agotado')
        assert agot['severidad'] == Evento.IMPORTANTE


def test_stock_no_vendible_se_ignora(app):
    with app.app_context():
        # Stock sin PrecioColegio → no es vendible → no genera evento
        db.session.add(Stock(id_colegio=9, id_producto=9, talla_individual='M', cantidad=0))
        db.session.commit()
        assert ee.detectar_stock() == []


def test_detecta_cartera_por_dias(app):
    _base(app)
    with app.app_context():
        vieja = date.today() - timedelta(days=40)
        media = date.today() - timedelta(days=20)
        nueva = date.today() - timedelta(days=2)
        for i, (f, saldo) in enumerate([(vieja, 5000), (media, 3000), (nueva, 9000)], start=1):
            db.session.add(Factura(numero_factura=f'F{i}', id_colegio=1, fecha_factura=f,
                                   total=10000, saldo_pendiente=saldo, estado='PENDIENTE',
                                   usuario_creacion='t'))
        db.session.commit()
        cands = ee.detectar_cartera()
        # la de 2 días no entra; la de 40 es CRITICO; la de 20 es IMPORTANTE
        assert len(cands) == 2
        sev = {c['datos']['numero']: c['severidad'] for c in cands}
        assert sev['F1'] == Evento.CRITICO
        assert sev['F2'] == Evento.IMPORTANTE


def test_venta_presencial_sin_descuento_se_marca(app):
    _base(app)
    with app.app_context():
        f = Factura(numero_factura='V1', id_colegio=1, fecha_factura=date.today(),
                    total=40000, saldo_pendiente=0, estado='PAGADA',
                    canal='PRESENCIAL', usuario_creacion='t')
        db.session.add(f)
        db.session.commit()
        db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1,
                                      talla_individual='M', cantidad=1,
                                      precio_unitario=40000, total_linea=40000))
        db.session.commit()
        cands = ee.detectar_ventas_sin_descuento()
        assert any(c['tipo'] == 'venta_sin_descuento' for c in cands)


def test_registrar_eventos_dedup(app):
    _base(app)
    with app.app_context():
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=0))
        db.session.commit()
        n1 = ee.registrar_eventos(ee.detectar_stock())
        assert len(n1) == 1
        # segunda pasada: el mismo hecho no se duplica
        n2 = ee.registrar_eventos(ee.detectar_stock())
        assert n2 == []
        assert Evento.query.filter_by(tipo='stock_agotado').count() == 1


def test_observar_prioriza_y_resume(app):
    _base(app)
    with app.app_context():
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=0))
        db.session.add(Factura(numero_factura='F1', id_colegio=1,
                               fecha_factura=date.today() - timedelta(days=40),
                               total=10000, saldo_pendiente=5000, estado='PENDIENTE',
                               usuario_creacion='t'))
        db.session.commit()
        r = ee.observar(persistir=True)
        assert r['hay_algo'] is True
        assert r['resumen']['CRITICO'] >= 1        # la cartera vieja
        assert r['resumen']['IMPORTANTE'] >= 1     # el stock agotado
        # el primero de la lista es el de mayor severidad (CRITICO antes que IMPORTANTE)
        assert r['eventos'][0]['severidad'] == 'CRITICO'
