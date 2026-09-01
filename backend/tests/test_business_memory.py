"""
Business Memory: reglas del negocio, presupuesto de compras, objetivos con
progreso en vivo, Autonomous Action Guard con conflicto de reglas, y Home.
"""
from datetime import date, timedelta

from app import db
from app.models import (
    Colegio, Producto, PrecioColegio, Stock, Factura, FacturaDetalle,
    ReglaNegocio, Objetivo, Evento,
)
from app.services import business_memory as bm
from app.services import event_engine as ee


def test_presupuesto_compras_bloquea_sobre_limite(app):
    with app.app_context():
        r = ReglaNegocio(categoria='COMPRAS', texto='No comprar más de $10M/mes')
        r.set_parametros({'limite': 10_000_000, 'periodo': 'mensual'})
        db.session.add(r)
        db.session.commit()
        ok, lim, _ = bm.verificar_presupuesto_compras(8_000_000)
        assert ok and lim == 10_000_000
        no_ok, lim2, msg = bm.verificar_presupuesto_compras(12_000_000)
        assert (not no_ok) and lim2 == 10_000_000 and 'presupuesto' in msg.lower()


def test_progreso_objetivo_en_vivo(app):
    with app.app_context():
        hoy = date.today()
        db.session.add(Objetivo(tipo='VENTAS', descripcion='Ventas del mes',
                                meta=1_000_000, anio=hoy.year, mes=hoy.month))
        db.session.add(Factura(numero_factura='F1', id_colegio=1, fecha_factura=hoy,
                               total=400_000, saldo_pendiente=0, estado='PAGADA',
                               usuario_creacion='t'))
        # una anulada NO cuenta
        db.session.add(Factura(numero_factura='F2', id_colegio=1, fecha_factura=hoy,
                               total=999_000, saldo_pendiente=0, estado='ANULADA',
                               usuario_creacion='t'))
        db.session.commit()
        metas = bm.progreso_objetivos()
        assert len(metas) == 1
        assert metas[0]['actual'] == 400_000
        assert metas[0]['pct'] == 40


def test_reglas_texto_para_prompt(app):
    with app.app_context():
        db.session.add(ReglaNegocio(categoria='PRECIO', texto='No vender por debajo de $45.000'))
        db.session.commit()
        t = bm.reglas_texto()
        assert 'PRECIO' in t and '45.000' in t


def _escenario_reposicion_costosa():
    """Prenda que se agota rápido y cuya reposición supera un presupuesto bajo."""
    db.session.add(Colegio(id_colegio=1, nombre='Manyanet'))
    db.session.add(Producto(id_producto=1, nombre='Blusa Niña'))
    db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='M',
                                 precio_unitario=40000, costo_unitario=25000))
    from app.models import Usuario
    db.session.add(Usuario(usuario='admin', contrasena_hash='x', rol='administrador'))
    db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=4))
    db.session.commit()
    f = Factura(numero_factura='V1', id_colegio=1, fecha_factura=date.today() - timedelta(days=1),
                total=720000, saldo_pendiente=0, estado='PAGADA', canal='PRESENCIAL',
                usuario_creacion='t')
    db.session.add(f)
    db.session.commit()
    db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1, talla_individual='M',
                                  cantidad=18, precio_unitario=40000, total_linea=720000))
    db.session.commit()


def test_guard_respeta_regla_de_presupuesto(app):
    with app.app_context():
        _escenario_reposicion_costosa()
        # Presupuesto ridículamente bajo → cualquier reposición lo supera
        r = ReglaNegocio(categoria='COMPRAS', texto='Tope $1.000/mes')
        r.set_parametros({'limite': 1000, 'periodo': 'mensual'})
        db.session.add(r)
        db.session.commit()
        ee.set_modo_observador('AUTONOMO')
        cands = ee.escanear(analizar_eventos=True)
        ev = next(c for c in cands if c['datos'].get('talla') == 'M')
        # el analyzer estimó un costo de reposición > presupuesto
        assert ev['datos'].get('costo_estimado', 0) > 1000
        # construimos un Evento para pasar por el Guard
        e = Evento(tipo=ev['tipo'], severidad=ev['severidad'], titulo=ev['titulo'],
                   score=ev['score'], clave_dedup=ev['clave_dedup'], estado='NUEVO')
        e.set_datos(ev['datos'])
        db.session.add(e)
        db.session.commit()
        permitido, motivo = ee.puede_auto(e, ev['datos'].get('accion_sugerida'))
        assert not permitido and 'presupuesto' in motivo.lower()


def test_home_arma_briefing(app):
    with app.app_context():
        hoy = date.today()
        db.session.add(Objetivo(tipo='VENTAS', descripcion='Ventas', meta=1_000_000,
                                anio=hoy.year, mes=hoy.month))
        db.session.add(Factura(numero_factura='F9', id_colegio=1, fecha_factura=hoy,
                               total=300_000, saldo_pendiente=50_000, estado='PENDIENTE',
                               usuario_creacion='t'))
        db.session.commit()
        h = bm.resumen_home()
        assert 'alertas' in h and 'metas' in h
        assert h['cartera_pendiente'] == 50_000
        assert h['metas'][0]['actual'] == 300_000
