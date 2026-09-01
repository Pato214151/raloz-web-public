"""
Ventas por día de la semana (para decisiones tipo '¿contrato para lunes/sábado?').
"""
from datetime import date

from app import db
from app.models import Factura
from app.api.asistente import _tool_ventas_por_dia


def _fac(num, f, total):
    db.session.add(Factura(numero_factura=num, id_colegio=1, fecha_factura=f,
                           total=total, saldo_pendiente=0, estado='PAGADA',
                           usuario_creacion='t'))


def test_agrupa_por_dia_de_semana_y_promedia(app):
    with app.app_context():
        # 2026-09-07 y 2026-09-14 son LUNES; 2026-09-05 es SÁBADO
        _fac('L1', date(2026, 9, 7), 100000)
        _fac('L2', date(2026, 9, 14), 300000)   # lunes total 400.000 en 2 lunes
        _fac('S1', date(2026, 9, 5), 50000)     # sábado
        # una anulada NO cuenta
        db.session.add(Factura(numero_factura='X', id_colegio=1, fecha_factura=date(2026, 9, 7),
                               total=999999, saldo_pendiente=0, estado='ANULADA',
                               usuario_creacion='t'))
        db.session.commit()
        r = _tool_ventas_por_dia('2026-09-01', '2026-09-30', ['lunes', 'sabado'])
        dias = {d['dia']: d for d in r['dias']}
        assert set(dias) == {'lunes', 'sábado'}
        assert dias['lunes']['total'] == 400000
        assert dias['lunes']['facturas'] == 2         # la anulada quedó fuera
        assert dias['lunes']['ocurrencias'] == 4      # sept 2026 tiene 4 lunes
        assert dias['lunes']['promedio_por_dia'] == 100000  # 400.000 / 4 lunes
        assert dias['sábado']['total'] == 50000


def test_sin_filtro_devuelve_los_siete_dias(app):
    with app.app_context():
        r = _tool_ventas_por_dia('2026-09-01', '2026-09-30', None)
        assert len(r['dias']) == 7
