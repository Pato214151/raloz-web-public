"""
El pedido web guarda si el cliente recoge en el local o pide envío.

La tienda ya preguntaba "Local o Envío" y mandaba el dato, pero el backend lo
descartaba: al llegar un pedido no había forma de saber si empacarlo para
despacho o dejarlo apartado, y tocaba llamar al cliente a preguntar.
"""
from app import db
from app.models import PedidoWeb


def _pedido(metodo):
    return PedidoWeb(
        referencia=f'REF-{metodo}', nombre_cliente='Ana', email_cliente='a@a.com',
        items_json='[]', total=100000, metodo_entrega=metodo,
    )


def test_guarda_envio(app):
    with app.app_context():
        db.session.add(_pedido('envio'))
        db.session.commit()
        assert PedidoWeb.query.filter_by(referencia='REF-envio').first().metodo_entrega == 'envio'


def test_guarda_local(app):
    with app.app_context():
        db.session.add(_pedido('local'))
        db.session.commit()
        assert PedidoWeb.query.filter_by(referencia='REF-local').first().metodo_entrega == 'local'


def test_to_dict_lo_expone_y_por_defecto_es_local(app):
    """Los pedidos viejos no traen el dato: se leen como 'local', que es lo
    que se asumía antes de que la tienda preguntara."""
    with app.app_context():
        p = _pedido('local')
        p.metodo_entrega = None
        db.session.add(p)
        db.session.commit()
        assert p.to_dict()['metodo_entrega'] == 'local'
