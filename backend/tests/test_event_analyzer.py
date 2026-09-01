"""
Event Analyzer + memoria (auto-resolución) + agrupación.

Prueba que un evento crudo se convierta en análisis con contexto de ventas,
score, severidad escalada y recomendación; que la memoria cierre lo resuelto;
y que las alertas de una misma prenda se agrupen.
"""
from datetime import date, timedelta

from app import db
from app.models import (
    Stock, PrecioColegio, Producto, Colegio, Factura, FacturaDetalle, Evento,
)
from app.services import event_engine as ee
from app.services import event_analyzer as ea


def _catalogo():
    db.session.add(Colegio(id_colegio=1, nombre='Manyanet'))
    db.session.add(Producto(id_producto=1, nombre='Blusa Niña'))
    for talla in ('8', '10', '12', 'M'):
        db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo=talla,
                                     precio_unitario=40000, costo_unitario=25000))
    db.session.commit()


def _venta(numero, talla, cantidad, dias_atras=1):
    f = Factura(numero_factura=numero, id_colegio=1,
                fecha_factura=date.today() - timedelta(days=dias_atras),
                total=40000 * cantidad, saldo_pendiente=0, estado='PAGADA',
                canal='PRESENCIAL', usuario_creacion='t')
    db.session.add(f)
    db.session.commit()
    db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1,
                                  talla_individual=talla, cantidad=cantidad,
                                  precio_unitario=40000, total_linea=40000 * cantidad))
    db.session.commit()


def test_stock_con_ventas_altas_escala_a_critico_y_recomienda_reponer(app):
    with app.app_context():
        _catalogo()
        # Quedan 4, se vendieron 18 en la última semana → riesgo de quiebre
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=4))
        db.session.commit()
        _venta('V1', 'M', 10, dias_atras=1)
        _venta('V2', 'M', 8, dias_atras=3)

        cands = ee.escanear(analizar_eventos=True)
        m = next(c for c in cands if c['datos'].get('talla') == 'M')
        assert m['severidad'] == 'CRITICO'           # escaló de 🟡 a 🔴 por el ritmo
        assert m['score'] >= 80
        assert 'reposición' in (m['recomendacion'] or '').lower()
        assert m['datos'].get('accion_sugerida', {}).get('tipo') == 'crear_tarea'
        assert 'se vendieron 18' in m['datos']['analisis']


def test_stock_bajo_sin_ventas_no_es_critico(app):
    with app.app_context():
        _catalogo()
        db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='8', cantidad=2))
        db.session.commit()  # sin ventas
        cands = ee.escanear(analizar_eventos=True)
        c = next(c for c in cands if c['datos'].get('talla') == '8')
        assert c['severidad'] != 'CRITICO'
        assert c['datos'].get('accion_sugerida') is None


def test_priority_score_pondera_urgencia():
    alto = ea.priority_score(impacto=90, urgencia=95, probabilidad=75)
    bajo = ea.priority_score(impacto=90, urgencia=10, probabilidad=75)
    assert alto > bajo and 0 <= alto <= 100


def test_memoria_auto_resuelve_lo_arreglado(app):
    with app.app_context():
        _catalogo()
        st = Stock(id_colegio=1, id_producto=1, talla_individual='8', cantidad=0)
        db.session.add(st)
        db.session.commit()
        ee.observar(persistir=True)
        assert Evento.query.filter_by(estado='NUEVO', tipo='stock_agotado').count() == 1
        # el Jefe repone → el evento debe cerrarse solo en el próximo escaneo
        st.cantidad = 50
        db.session.commit()
        r = ee.observar(persistir=True)
        assert r['resueltos'] >= 1
        assert Evento.query.filter_by(estado='RESUELTO', tipo='stock_agotado').count() == 1


def test_agrupa_varias_tallas_de_la_misma_prenda(app):
    with app.app_context():
        _catalogo()
        for talla in ('8', '10', '12'):
            db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual=talla, cantidad=1))
        db.session.commit()
        r = ee.observar(persistir=True)
        grupos = [it for it in r['items'] if it.get('tipo') == 'grupo_stock']
        assert len(grupos) == 1
        assert '3 tallas' in grupos[0]['titulo']
