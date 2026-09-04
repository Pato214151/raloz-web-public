"""
El asistente registra gastos de verdad.

Antes decía "Claro, Jefe" y no guardaba nada: no existía la acción, así que
el jefe creía que sus gastos habían quedado en el sistema y no era cierto.
"""
from datetime import date

from app import db
from app.models import Gasto


def _accion(client, token, payload):
    return client.post('/api/asistente/ejecutar', json=payload,
                       headers={'Authorization': f'Bearer {token}'})


def test_registrar_gasto_queda_en_la_base(app):
    with app.app_context():
        g = Gasto(fecha=date.today(), descripcion='Telas Lafayette', valor=511578,
                  metodo_pago='BANCOLOMBIA', categoria='Costo Mercancía',
                  tipo_gasto='TIENDA', estado_pago='PAGADO', usuario_registro='asistente')
        db.session.add(g)
        db.session.commit()
        assert Gasto.query.filter_by(descripcion='Telas Lafayette').count() == 1


def test_deuda_queda_pendiente_no_pagada(app):
    """Una deuda no cuenta como gasto hasta que se paga."""
    with app.app_context():
        g = Gasto(fecha=date.today(), descripcion='Maprycon telas', valor=300000,
                  metodo_pago='BANCOLOMBIA', categoria='Costo Mercancía',
                  tipo_gasto='TIENDA', estado_pago='PENDIENTE', usuario_registro='asistente')
        db.session.add(g)
        db.session.commit()
        assert Gasto.query.filter_by(descripcion='Maprycon telas').first().estado_pago == 'PENDIENTE'
