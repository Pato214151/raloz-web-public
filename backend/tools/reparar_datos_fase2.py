"""
Reparación de datos de la Fase 2 — correcciones aprobadas por el dueño
(2026-07-06) sobre los hallazgos de tools/diagnostico_datos.py:

  1. Precios de uniforme COMPLETO más caros que la suma de sus piezas
     → completo = suma exacta de las piezas (decisión del dueño)
  2. Prendas pendientes PENDIENTES de facturas ANULADAS → CANCELADA
  3. stock_pendiente_fabricacion con ids_pedidos rotos → se limpian las
     referencias; si no queda ningún pedido válido → completado
  4. Kardex desincronizado → AJUSTE al stock actual (el stock manda)
  5. Facturas con total_abonado > suma de pagos (saldos pagados por MP
     sin registro de Pago) → se crea el Pago faltante
  6. Facturas con pagos > total_abonado (totales rancios) → se recalculan
     desde los pagos

Uso:
  python tools/reparar_datos_fase2.py            # simulacro: solo muestra qué haría
  python tools/reparar_datos_fase2.py --confirm  # aplica los cambios

⚠ Corre primero un respaldo:  python tools/backup_db.py
Cada cambio queda registrado en la tabla auditoria (usuario reparacion_fase2).
"""
import os
import sys
from collections import defaultdict
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# El script vive en tools/; el paquete `app` está un nivel arriba (backend/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app import create_app, db
from app.models import (
    Auditoria, Factura, Pago, PrendaPendiente, StockPendienteFabricacion,
    PedidoFabricacion, Stock, MovimientoInventario, PrecioColegio,
    Producto, Colegio,
)
from app.utils.inventario import registrar_movimiento

USUARIO = 'reparacion_fase2'

COMBOS_UNIFORME = {
    'UNI-DIARIO-NINO':   ['PD-NINO', 'CC-NINO', 'BLAZER', 'CHALECO'],
    'UNI-DIARIO-NINA':   ['JARDINERA', 'BLUSA', 'BLAZER', 'CHALECO'],
    'UNI-EDU':           ['PANT-EDU', 'CAMISETA', 'CHQ-EDU', 'PANTALONETA'],
    'UNI-DIARIO-NINO-M': ['PD-NINO', 'CC-NINO', 'BLAZER', 'CHALECO'],
    'UNI-DIARIO-NINA-M': ['JARDINERA', 'BLUSA', 'BLAZER', 'CHALECO'],
}


def auditar(tabla, id_registro, accion, comentario):
    db.session.add(Auditoria(tabla_afectada=tabla, id_registro=id_registro,
                             accion=accion, usuario=USUARIO, comentario=comentario))


def reparar(aplicar: bool):
    cambios = 0

    # ── 1. Uniformes COMPLETOS más caros que la suma → suma exacta ────────
    print('\n1. Precios de uniformes COMPLETOS con sobreprecio → suma exacta')
    prod_por_codigo = {p.codigo: p for p in Producto.query.all() if p.codigo}
    colegios = {c.id_colegio: c.nombre for c in Colegio.query.all()}
    precios = defaultdict(dict)
    filas = {}
    for pr in PrecioColegio.query.all():
        precios[(pr.id_colegio, pr.id_producto)][pr.talla_grupo] = float(pr.precio_unitario)
        filas[(pr.id_colegio, pr.id_producto, pr.talla_grupo)] = pr

    for cod_uni, cod_piezas in COMBOS_UNIFORME.items():
        uni = prod_por_codigo.get(cod_uni)
        piezas = [prod_por_codigo.get(c) for c in cod_piezas]
        if not uni or any(p is None for p in piezas):
            continue
        for id_col, nombre_col in colegios.items():
            for talla, precio_uni in precios.get((id_col, uni.id_producto), {}).items():
                suma = 0
                completo = True
                for pieza in piezas:
                    v = precios.get((id_col, pieza.id_producto), {}).get(talla)
                    if v is None:
                        completo = False
                        break
                    suma += v
                if not completo or precio_uni <= suma:
                    continue
                fila = filas[(id_col, uni.id_producto, talla)]
                print(f'   {nombre_col} {cod_uni} T{talla}: {precio_uni:.0f} → {suma:.0f}')
                cambios += 1
                if aplicar:
                    fila.precio_unitario = suma
                    auditar('precios_colegio', fila.id_precio, 'REPARACION_PRECIO',
                            f'{cod_uni} T{talla}: {precio_uni:.0f} → {suma:.0f} (= suma de piezas)')

    # ── 2. Prendas PENDIENTES de facturas ANULADAS → CANCELADA ────────────
    print('\n2. Prendas pendientes de facturas anuladas → CANCELADA')
    prendas = (PrendaPendiente.query
               .join(Factura, PrendaPendiente.id_factura == Factura.id_factura)
               .filter(Factura.estado == 'ANULADA',
                       PrendaPendiente.estado == 'PENDIENTE').all())
    for p in prendas:
        print(f'   #{p.id_pendiente} {p.producto_nombre} T{p.talla} (factura {p.numero_factura})')
        cambios += 1
        if aplicar:
            p.estado = 'CANCELADA'
            p.observaciones = f'{p.observaciones or ""} [CANCELADA: factura anulada]'.strip()
            auditar('prendas_pendientes', p.id_pendiente, 'REPARACION_CANCELAR',
                    f'Factura {p.numero_factura} anulada')

    # ── 3. stock_pendiente_fabricacion con referencias rotas ──────────────
    print('\n3. stock_pendiente_fabricacion con ids_pedidos rotos')
    for spf in StockPendienteFabricacion.query.filter_by(estado='pendiente').all():
        ids = [int(x) for x in (spf.ids_pedidos or '').split(',') if x.strip().isdigit()]
        validos = [i for i in ids if db.session.get(PedidoFabricacion, i)]
        if validos == ids:
            continue
        cambios += 1
        if not validos:
            print(f'   spf#{spf.id_pendiente} T{spf.talla}: sin pedidos válidos → completado (pendiente {spf.cantidad_pendiente} → 0)')
            if aplicar:
                auditar('stock_pendiente_fabricacion', spf.id_pendiente, 'REPARACION_CERRAR',
                        f'Pedidos {ids} ya no existen; pendiente {spf.cantidad_pendiente} → 0')
                spf.ids_pedidos = ''
                spf.cantidad_pendiente = 0
                spf.estado = 'completado'
        else:
            print(f'   spf#{spf.id_pendiente} T{spf.talla}: ids {ids} → {validos}')
            if aplicar:
                auditar('stock_pendiente_fabricacion', spf.id_pendiente, 'REPARACION_LIMPIAR_IDS',
                        f'ids {ids} → {validos}')
                spf.ids_pedidos = ','.join(str(i) for i in validos)

    # ── 4. Kardex desincronizado → AJUSTE al stock actual ─────────────────
    print('\n4. Kardex desincronizado → AJUSTE al stock actual')
    ultimo_mov = {}
    for m in MovimientoInventario.query.order_by(MovimientoInventario.fecha.asc(),
                                                 MovimientoInventario.id.asc()).all():
        ultimo_mov[(m.id_colegio, m.id_producto, m.talla_individual)] = m.stock_resultante
    for s in Stock.query.all():
        clave = (s.id_colegio, s.id_producto, s.talla_individual)
        if clave in ultimo_mov and (s.cantidad or 0) != (ultimo_mov[clave] or 0):
            print(f'   colegio={s.id_colegio} prod={s.id_producto} T{s.talla_individual}: '
                  f'kardex {ultimo_mov[clave]} → AJUSTE a {s.cantidad}')
            cambios += 1
            if aplicar:
                registrar_movimiento(s.id_colegio, s.id_producto, s.talla_individual,
                                     'AJUSTE', s.cantidad or 0, usuario=USUARIO,
                                     motivo='Resincronización kardex (reparación fase 2)')

    # ── 5 y 6. Facturas descuadradas ───────────────────────────────────────
    print('\n5-6. Facturas con totales que no cuadran con sus pagos')
    pagos_por_factura = dict(
        db.session.query(Pago.id_factura, func.coalesce(func.sum(Pago.valor), 0))
        .group_by(Pago.id_factura).all())
    for f in Factura.query.filter(Factura.estado != 'ANULADA').all():
        pagado = float(pagos_por_factura.get(f.id_factura, 0))
        abonado = float(f.total_abonado or 0)
        total = float(f.total or 0)
        saldo = float(f.saldo_pendiente or 0)
        if abs(abonado - pagado) <= 1 and abs(saldo - max(0, total - pagado)) <= 1:
            continue
        cambios += 1
        if abonado - pagado > 1:
            # Falta registro de Pago (saldo pagado por MP sin Pago)
            faltante = round(abonado - pagado, 2)
            print(f'   {f.numero_factura}: crear Pago faltante ${faltante:.0f} (MP) y recalcular')
            if aplicar:
                db.session.add(Pago(id_factura=f.id_factura, valor=faltante,
                                    metodo_pago='MP', usuario_registro=USUARIO,
                                    fecha_pago=date.today()))
                db.session.flush()
                f.recalcular_desde_pagos()
                auditar('facturas', f.id_factura, 'REPARACION_PAGO_FALTANTE',
                        f'Pago MP ${faltante:.0f} sin registro (saldo web); creado y recalculado')
        else:
            # Totales rancios: los pagos son la fuente de verdad
            print(f'   {f.numero_factura}: recalcular desde pagos '
                  f'(abonado {abonado:.0f} → {pagado:.0f}, saldo {saldo:.0f} → {max(0, total - pagado):.0f})')
            if pagado - total > 1:
                print(f'     ⚠ SOBREPAGO de ${pagado - total:.0f} — revisar posible devolución al cliente')
            if aplicar:
                f.recalcular_desde_pagos()
                auditar('facturas', f.id_factura, 'REPARACION_RECALCULO',
                        f'Totales recalculados desde pagos (abonado {abonado:.0f} → {pagado:.0f})')

    print(f'\n{"═" * 60}')
    if aplicar:
        db.session.commit()
        print(f'✅ {cambios} correcciones APLICADAS (auditadas como {USUARIO}).')
    else:
        db.session.rollback()
        print(f'SIMULACRO: {cambios} correcciones pendientes. Ejecuta con --confirm para aplicar.')


if __name__ == '__main__':
    aplicar = '--confirm' in sys.argv
    app = create_app()
    with app.app_context():
        reparar(aplicar)
