"""
Autonomía del Observador: modos SUGERIR / PREPARAR / AUTONOMO + push.

Verifica que en AUTÓNOMO se ejecuten SOLO acciones de bajo riesgo (crear
recordatorio), que queden en la bitácora, y que en SUGERIR no se ejecute nada.
"""
from datetime import date, timedelta

from app import db
from app.models import (
    Stock, PrecioColegio, Producto, Colegio, Factura, FacturaDetalle,
    Usuario, Tarea, AccionAsistente, ConfigSitio,
)
from app.services import event_engine as ee


def _escenario_riesgo():
    """Catálogo + admin + una prenda que se agota rápido (evento CRÍTICO con
    acción sugerida crear_tarea)."""
    db.session.add(Colegio(id_colegio=1, nombre='Manyanet'))
    db.session.add(Producto(id_producto=1, nombre='Blusa Niña'))
    db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='M',
                                 precio_unitario=40000, costo_unitario=25000))
    db.session.add(Usuario(usuario='admin', contrasena_hash='x', rol='administrador'))
    db.session.add(Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=4))
    db.session.commit()
    f = Factura(numero_factura='V1', id_colegio=1, fecha_factura=date.today() - timedelta(days=1),
                total=400000, saldo_pendiente=0, estado='PAGADA', canal='PRESENCIAL',
                usuario_creacion='t')
    db.session.add(f)
    db.session.commit()
    db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1, talla_individual='M',
                                  cantidad=18, precio_unitario=40000, total_linea=720000))
    db.session.commit()


def test_modo_por_defecto_y_cambio(app):
    with app.app_context():
        assert ee.modo_observador() == ee.MODO_AUTONOMO   # por defecto autónomo
        assert ee.set_modo_observador('SUGERIR') == 'SUGERIR'
        assert ee.modo_observador() == 'SUGERIR'
        assert ee.set_modo_observador('inventado') is None   # inválido → no cambia
        assert ee.modo_observador() == 'SUGERIR'


def test_modo_autonomo_crea_tarea_y_la_registra(app):
    with app.app_context():
        _escenario_riesgo()
        ee.set_modo_observador('AUTONOMO')
        ee.observar(persistir=True)
        # creó el recordatorio de reposición…
        assert Tarea.query.count() == 1
        # …y lo dejó en la bitácora (auditable + reversible)
        acc = AccionAsistente.query.filter_by(tipo='crear_tarea').first()
        assert acc is not None and acc.reversible and acc.usuario == '[Observador]'


def test_modo_sugerir_no_ejecuta_nada(app):
    with app.app_context():
        _escenario_riesgo()
        ee.set_modo_observador('SUGERIR')   # en SUGERIR no ejecuta acciones solo
        ee.observar(persistir=True)
        assert Tarea.query.count() == 0
        assert AccionAsistente.query.count() == 0


def test_push_resumen_sin_relevantes_no_envia(app):
    with app.app_context():
        # sin eventos → nada relevante → 0 push (y no revienta aunque no haya VAPID)
        r = {'resumen': {'CRITICO': 0, 'IMPORTANTE': 0, 'PRECAUCION': 0, 'INFORMATIVO': 0}}
        assert ee.push_resumen(r) == 0
