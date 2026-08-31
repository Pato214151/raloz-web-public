"""
Bitácora + verificación robusta + rollback del Asistente.

Prueba directamente las funciones puras (sin JWT/HTTP): journaling, la
verificación contra la fuente de verdad, y la reversión de cada tipo de acción.
"""
from app import db
from app.models import Stock, PrecioColegio, Tarea, AccionAsistente
from app.api.asistente import (
    _registrar_accion, _verificar_accion, _revertir_accion,
)


def _accion(tipo, antes, despues, reversible=True):
    acc = AccionAsistente(tipo=tipo, descripcion='test', reversible=reversible,
                          verificado=False, resultado='EJECUTADA', usuario='u')
    acc.set_antes(antes)
    acc.set_despues(despues)
    db.session.add(acc)
    db.session.commit()
    return acc


def test_registrar_accion_guarda_snapshots_y_resultado(app):
    with app.app_context():
        acc = _registrar_accion('ajustar_stock', 'desc', {'a': 1}, {'b': 2},
                                reversible=True, verificado=True, usuario='juan')
        assert acc is not None
        recargada = AccionAsistente.query.get(acc.id_accion)
        assert recargada.resultado == 'VERIFICADA'      # verificado=True → VERIFICADA
        assert recargada.reversible is True
        assert recargada.antes == {'a': 1}
        assert recargada.despues == {'b': 2}

        fallida = _registrar_accion('ajustar_stock', 'd', {}, {}, reversible=True,
                                    verificado=False, usuario='juan')
        assert fallida.resultado == 'FALLO_VERIFICACION'  # verificado=False


def test_verificar_ajustar_stock_contra_bd(app):
    with app.app_context():
        st = Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=10)
        db.session.add(st)
        db.session.commit()
        # coincide con la BD → verificado
        assert _verificar_accion('ajustar_stock', {'id_stock': st.id_stock, 'cantidad': 10})
        # NO coincide → no verificado (no asumas que funcionó)
        assert not _verificar_accion('ajustar_stock', {'id_stock': st.id_stock, 'cantidad': 3})


def test_rollback_ajustar_stock_restaura_cantidad(app):
    with app.app_context():
        st = Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=10)
        db.session.add(st)
        db.session.commit()
        # La acción subió de 3 → 10; revertir debe dejarlo en 3.
        acc = _accion('ajustar_stock',
                      antes={'id_colegio': 1, 'id_producto': 1, 'talla': 'M', 'cantidad': 3},
                      despues={'id_stock': st.id_stock, 'cantidad': 10})
        ok, msg, verificado = _revertir_accion(acc, 'juan')
        assert ok and verificado
        assert Stock.query.get(st.id_stock).cantidad == 3


def test_rollback_fijar_costo_restaura_costos(app):
    with app.app_context():
        r = PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='M',
                          precio_unitario=40000, costo_unitario=25000)
        db.session.add(r)
        db.session.commit()
        # La acción cambió el costo a 30000; revertir debe volver a 25000.
        r.costo_unitario = 30000
        db.session.commit()
        acc = _accion('fijar_costo',
                      antes={'filas': [{'id_precio': r.id_precio, 'costo': 25000}]},
                      despues={'ids_precio': [r.id_precio], 'costo': 30000})
        ok, msg, verificado = _revertir_accion(acc, 'juan')
        assert ok and verificado
        assert PrecioColegio.query.get(r.id_precio).costo_unitario == 25000


def test_rollback_crear_tarea_elimina_la_tarea(app):
    with app.app_context():
        t = Tarea(titulo='recordatorio de prueba', creada_por=1)
        db.session.add(t)
        db.session.commit()
        tid = t.id_tarea
        acc = _accion('crear_tarea', antes={}, despues={'id_tarea': tid})
        ok, msg, verificado = _revertir_accion(acc, 'juan')
        assert ok and verificado
        assert Tarea.query.get(tid) is None


def test_accion_no_reversible_no_se_revierte(app):
    with app.app_context():
        acc = _accion('desconocida', antes={}, despues={}, reversible=False)
        ok, msg, verificado = _revertir_accion(acc, 'juan')
        assert not ok
