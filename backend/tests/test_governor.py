"""
Self-Check / Governor: checklist pre-ejecución, verificación post, y cierre
de eventos relacionados (Actions → Proactivity).
"""
from app import db
from app.models import Stock, Evento, ReglaNegocio
from app.services import governor


def test_pre_check_ok_para_accion_valida(app):
    with app.app_context():
        r = governor.pre_check({'tipo': 'ajustar_stock'})
        assert r['ok']
        assert any(c['clave'] == 'reversible' and c['estado'] == 'ok' for c in r['checklist'])
        assert any(c['clave'] == 'verificable' and c['estado'] == 'ok' for c in r['checklist'])


def test_pre_check_bloquea_sin_tipo(app):
    with app.app_context():
        r = governor.pre_check({})
        assert not r['ok'] and r['bloqueos']


def test_pre_check_bloquea_compra_sobre_presupuesto(app):
    with app.app_context():
        reg = ReglaNegocio(categoria='COMPRAS', texto='tope bajo')
        reg.set_parametros({'limite': 1000, 'periodo': 'mensual'})
        db.session.add(reg)
        db.session.commit()
        r = governor.pre_check({'tipo': 'crear_tarea', 'monto': 5000})
        assert not r['ok']
        assert any(c['clave'] == 'reglas' and c['estado'] == 'fail' for c in r['checklist'])


def test_verificar_contra_bd(app):
    with app.app_context():
        st = Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=7)
        db.session.add(st)
        db.session.commit()
        assert governor.verificar('ajustar_stock', {'id_stock': st.id_stock, 'cantidad': 7})
        assert not governor.verificar('ajustar_stock', {'id_stock': st.id_stock, 'cantidad': 3})


def test_post_check_cierra_evento_relacionado(app):
    with app.app_context():
        st = Stock(id_colegio=1, id_producto=1, talla_individual='M', cantidad=0)
        db.session.add(st)
        db.session.commit()
        ev = Evento(tipo='stock_agotado', severidad='IMPORTANTE', titulo='Agotado',
                    clave_dedup=f'stock_agotado:{st.id_stock}', estado='NUEVO',
                    entidad_tipo='stock', entidad_id=st.id_stock)
        db.session.add(ev)
        db.session.commit()
        # el Jefe repone → la acción resuelve el problema y el Governor cierra la alerta
        st.cantidad = 50
        db.session.commit()
        post = governor.post_check('ajustar_stock', {'id_stock': st.id_stock, 'cantidad': 50})
        assert post['verificado'] and post['eventos_cerrados'] == 1
        assert Evento.query.get(ev.id_evento).estado == 'RESUELTO'
