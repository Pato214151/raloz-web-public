"""
Herramientas de negocio nuevas: gastos, flujo de caja, simular devolución,
y el gate que decide cuándo se permite el Observador.
"""
from datetime import date

from app import db
from app.models import Gasto, Pago, Factura, FacturaDetalle, PrecioColegio
from app.api import asistente as a


def test_gastos_por_categoria(app):
    with app.app_context():
        hoy = date.today()
        db.session.add(Gasto(fecha=hoy, descripcion='arriendo', valor=800000,
                             metodo_pago='EFECTIVO', categoria='Arriendo',
                             usuario_registro='t'))
        db.session.add(Gasto(fecha=hoy, descripcion='hilos', valor=50000,
                             metodo_pago='EFECTIVO', categoria='Insumos',
                             usuario_registro='t'))
        db.session.commit()
        r = a._tool_gastos(None, None)
        assert r['total'] == 850000
        assert r['categorias'][0]['categoria'] == 'Arriendo'   # ordenado desc


def test_flujo_caja_ingresos_menos_gastos(app):
    with app.app_context():
        hoy = date.today()
        f = Factura(numero_factura='F1', id_colegio=1, fecha_factura=hoy, total=100000,
                    saldo_pendiente=0, estado='PAGADA', usuario_creacion='t')
        db.session.add(f)
        db.session.commit()
        db.session.add(Pago(id_factura=f.id_factura, fecha_pago=hoy, valor=100000,
                            metodo_pago='EFECTIVO', usuario_registro='t'))
        db.session.add(Gasto(fecha=hoy, descripcion='x', valor=30000, metodo_pago='EFECTIVO',
                             categoria='Otros', estado_pago='PAGADO', usuario_registro='t'))
        db.session.commit()
        r = a._tool_flujo_caja(None, None)
        assert r['ingresos'] == 100000 and r['egresos'] == 30000 and r['neto'] == 70000


def test_simular_devolucion_calcula_impacto(app):
    with app.app_context():
        f = Factura(numero_factura='V9', id_colegio=1, fecha_factura=date.today(),
                    total=40000, total_abonado=40000, saldo_pendiente=0, estado='PAGADA',
                    usuario_creacion='t')
        db.session.add(f)
        # talla 'M' pertenece al grupo 'S-M' (así se guardan los precios/costos)
        db.session.add(PrecioColegio(id_colegio=1, id_producto=1, talla_grupo='S-M',
                                     precio_unitario=40000, costo_unitario=25000))
        db.session.commit()
        db.session.add(FacturaDetalle(id_factura=f.id_factura, id_producto=1,
                                      talla_individual='M', cantidad=1,
                                      precio_unitario=40000, total_linea=40000))
        db.session.commit()
        r = a._tool_simular_devolucion('V9')
        assert r['a_devolver'] == 40000 and r['impacto_caja'] == -40000
        assert r['unidades_regresan'] == 1
        assert r['utilidad_que_se_pierde'] == 15000   # 40000 - 25000 (costo real)
        assert r['estimado'] is False


def test_gate_observador_solo_en_revision():
    assert a._es_revision('¿cómo está el negocio?') is True
    assert a._es_revision('revisa todo') is True
    assert a._es_revision('buenos días') is True
    assert a._es_revision('¿me conviene contratar a alguien?') is False
    assert a._es_revision('quiero reducir gastos') is False
