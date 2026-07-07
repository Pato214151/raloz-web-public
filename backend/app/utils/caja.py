"""
Conciliación con la caja física.

registrar_ingreso_efectivo() es el único punto donde un cobro en EFECTIVO
entra a la caja diaria: lo usan el abono inicial de crear_factura, los pagos
de saldo (/api/pagos) y el saldo de fabricación cobrado en el local. Antes
solo el abono inicial se registraba y la caja descuadraba al cerrar.
"""
from datetime import datetime

from app import db
from app.models import CajaDiaria, MovimientoCaja


def registrar_ingreso_efectivo(concepto, valor, usuario):
    """Si hay caja ABIERTA, registra un INGRESO en efectivo y actualiza los
    totales esperados. Si no hay caja abierta no hace nada (mismo criterio
    que tenía crear_factura). No hace commit. Devuelve el movimiento o None."""
    if not valor or valor <= 0:
        return None
    caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
    if not caja:
        return None

    mov = MovimientoCaja(
        id_caja=caja.id_caja, tipo='INGRESO',
        concepto=concepto, valor=valor,
        metodo_pago='EFECTIVO', usuario=usuario,
        fecha_hora=datetime.utcnow(),
    )
    db.session.add(mov)
    caja.total_ventas = (caja.total_ventas or 0) + valor
    caja.monto_esperado = (caja.monto_inicial or 0) + (caja.total_ventas or 0) - (caja.total_gastos or 0)
    return mov
