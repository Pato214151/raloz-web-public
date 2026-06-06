"""
Tests del kardex (movimientos de inventario).

Blindan la regla más importante de la Fase 1: una ENTRADA SUMA al stock
(no lo reemplaza), una SALIDA resta con piso en 0, y todo queda registrado.
"""
import pytest
from app import db
from app.models import Stock, MovimientoInventario
from app.utils.inventario import registrar_movimiento


def _stock():
    return Stock.query.filter_by(id_colegio=1, id_producto=1, talla_individual='10').first()


def test_entrada_suma_no_reemplaza(app):
    registrar_movimiento(1, 1, '10', 'ENTRADA', 5, usuario='u'); db.session.commit()
    assert _stock().cantidad == 5
    registrar_movimiento(1, 1, '10', 'ENTRADA', 3, usuario='u'); db.session.commit()
    assert _stock().cantidad == 8  # SUMA, NO reemplaza (el bug original)


def test_salida_resta_con_piso_en_cero(app):
    registrar_movimiento(1, 1, '10', 'ENTRADA', 4, usuario='u'); db.session.commit()
    registrar_movimiento(1, 1, '10', 'SALIDA', 10, usuario='u'); db.session.commit()
    assert _stock().cantidad == 0  # nunca negativo


def test_ajuste_fija_valor_absoluto(app):
    registrar_movimiento(1, 1, '10', 'ENTRADA', 4, usuario='u'); db.session.commit()
    registrar_movimiento(1, 1, '10', 'AJUSTE', 7, usuario='u'); db.session.commit()
    assert _stock().cantidad == 7


def test_kardex_registra_cada_movimiento(app):
    registrar_movimiento(1, 1, '10', 'ENTRADA', 5, usuario='ana'); db.session.commit()
    registrar_movimiento(1, 1, '10', 'SALIDA', 2, usuario='ana', motivo='Venta', referencia='FAC-1'); db.session.commit()
    movs = MovimientoInventario.query.order_by(MovimientoInventario.id).all()
    assert len(movs) == 2
    assert movs[0].tipo == 'ENTRADA' and movs[0].stock_resultante == 5
    assert movs[1].tipo == 'SALIDA' and movs[1].stock_resultante == 3
    assert movs[1].referencia == 'FAC-1' and movs[1].usuario == 'ana'


def test_tipo_invalido_lanza_error(app):
    with pytest.raises(ValueError):
        registrar_movimiento(1, 1, '10', 'ROBO', 5, usuario='u')
