"""
Diagnóstico de consistencia de datos — SOLO LECTURA (no modifica nada).

Revisa los puntos de la sección F de docs/ARQUITECTURA.md:
  1. Filas huérfanas en stock_pendiente / prendas_pendientes / stock_pendiente_fabricacion
  2. Facturas cuyos totales no cuadran con sus pagos
  3. Estados de entrega fuera del vocabulario conocido
  4. Pedidos web pagados sin factura
  5. Kardex desincronizado del stock real
  6. Precios de "uniforme COMPLETO" vs suma de sus piezas
  7. Reservas activas ya vencidas

Uso (el dueño, con su DATABASE_URL de producción o local):
  DATABASE_URL="postgresql://..." python tools/diagnostico_datos.py
"""
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# El script vive en tools/; el paquete `app` está un nivel arriba (backend/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from sqlalchemy import func

from app import create_app, db
from app.models import (
    Factura, Pago, PrendaPendiente, StockPendiente, StockPendienteFabricacion,
    PedidoFabricacion, PedidoWeb, Stock, MovimientoInventario,
    PrecioColegio, Producto, Colegio, Reserva,
)

ESTADOS_ENTREGA_CONOCIDOS = {
    'POR_ENTREGAR', 'LISTO_EMPAQUE', 'LISTO_LLAMAR', 'ENTREGADA',  # flujo local
    'EMPACADO', 'ENTREGADO',                                        # flujo web
}

# Composición de los uniformes completos, por código de producto
COMBOS_UNIFORME = {
    'UNI-DIARIO-NINO':   ['PD-NINO', 'CC-NINO', 'BLAZER', 'CHALECO'],
    'UNI-DIARIO-NINA':   ['JARDINERA', 'BLUSA', 'BLAZER', 'CHALECO'],
    'UNI-EDU':           ['PANT-EDU', 'CAMISETA', 'CHQ-EDU', 'PANTALONETA'],
    'UNI-DIARIO-NINO-M': ['PD-NINO', 'CC-NINO', 'BLAZER', 'CHALECO'],
    'UNI-DIARIO-NINA-M': ['JARDINERA', 'BLUSA', 'BLAZER', 'CHALECO'],
}


def seccion(titulo):
    print(f"\n{'═' * 70}\n{titulo}\n{'═' * 70}")


def diagnosticar():
    hallazgos = 0

    # ── 1a. stock_pendiente huérfano o de facturas anuladas ──────────────
    seccion('1a. stock_pendiente (mecanismo viejo)')
    total_sp = StockPendiente.query.count()
    huerfanos = (StockPendiente.query
                 .outerjoin(Factura, StockPendiente.id_factura == Factura.id_factura)
                 .filter(Factura.id_factura.is_(None)).count())
    de_anuladas = (StockPendiente.query
                   .join(Factura, StockPendiente.id_factura == Factura.id_factura)
                   .filter(Factura.estado == 'ANULADA').count())
    print(f"  Filas totales: {total_sp} | sin factura: {huerfanos} | de facturas ANULADAS: {de_anuladas}")
    hallazgos += huerfanos + de_anuladas

    # ── 1b. prendas_pendientes de facturas anuladas pero aún PENDIENTES ──
    seccion('1b. prendas_pendientes PENDIENTES de facturas anuladas')
    prendas_anuladas = (PrendaPendiente.query
                        .join(Factura, PrendaPendiente.id_factura == Factura.id_factura)
                        .filter(Factura.estado == 'ANULADA',
                                PrendaPendiente.estado == 'PENDIENTE').all())
    for p in prendas_anuladas[:10]:
        print(f"  #{p.id_pendiente} {p.producto_nombre} T{p.talla} x{p.cantidad} (factura {p.numero_factura})")
    print(f"  Total: {len(prendas_anuladas)}")
    hallazgos += len(prendas_anuladas)

    # ── 1c. stock_pendiente_fabricacion → ids_pedidos rotos ──────────────
    seccion('1c. stock_pendiente_fabricacion con ids_pedidos rotos')
    rotos = 0
    for spf in StockPendienteFabricacion.query.all():
        ids = [int(x) for x in (spf.ids_pedidos or '').split(',') if x.strip().isdigit()]
        faltan = [i for i in ids if not db.session.get(PedidoFabricacion, i)]
        if faltan:
            rotos += 1
            print(f"  spf#{spf.id_pendiente} ({spf.talla}, pendiente={spf.cantidad_pendiente}, "
                  f"estado={spf.estado}) → pedidos inexistentes: {faltan}")
    print(f"  Total con referencias rotas: {rotos}")
    hallazgos += rotos

    # ── 2. Facturas cuyos totales no cuadran con sus pagos ───────────────
    seccion('2. Facturas con totales que no cuadran (abonado/saldo vs pagos reales)')
    pagos_por_factura = dict(
        db.session.query(Pago.id_factura, func.coalesce(func.sum(Pago.valor), 0))
        .group_by(Pago.id_factura).all()
    )
    descuadradas = 0
    for f in Factura.query.filter(Factura.estado != 'ANULADA').all():
        pagado = float(pagos_por_factura.get(f.id_factura, 0))
        abonado = float(f.total_abonado or 0)
        saldo = float(f.saldo_pendiente or 0)
        total = float(f.total or 0)
        if abs(abonado - pagado) > 1 or abs(saldo - max(0, total - pagado)) > 1:
            descuadradas += 1
            if descuadradas <= 15:
                print(f"  {f.numero_factura}: total={total:.0f} abonado={abonado:.0f} "
                      f"pagos_reales={pagado:.0f} saldo={saldo:.0f} estado={f.estado}")
    print(f"  Total descuadradas: {descuadradas}")
    hallazgos += descuadradas

    # ── 3. Estados de entrega fuera de vocabulario ────────────────────────
    seccion('3. estado_entrega fuera del vocabulario conocido')
    raros = (db.session.query(Factura.estado_entrega, func.count())
             .filter(~Factura.estado_entrega.in_(ESTADOS_ENTREGA_CONOCIDOS))
             .group_by(Factura.estado_entrega).all())
    for estado, n in raros:
        print(f"  {estado!r}: {n} facturas")
        hallazgos += n
    if not raros:
        print("  Ninguno ✓")

    # ── 4. Pedidos web pagados sin factura ────────────────────────────────
    seccion('4. Pedidos web pagados SIN factura (webhook perdido sin reconciliar)')
    sin_factura = PedidoWeb.query.filter(
        PedidoWeb.estado == 'pagado', PedidoWeb.id_factura.is_(None)).all()
    for p in sin_factura[:10]:
        print(f"  {p.referencia} ${p.total:.0f} pagado={p.fecha_pago}")
    print(f"  Total: {len(sin_factura)}")
    hallazgos += len(sin_factura)

    # ── 5. Kardex vs stock real ────────────────────────────────────────────
    seccion('5. Kardex desincronizado (último stock_resultante ≠ stock actual)')
    ultimo_mov = {}
    for m in MovimientoInventario.query.order_by(MovimientoInventario.fecha.asc(),
                                                 MovimientoInventario.id.asc()).all():
        ultimo_mov[(m.id_colegio, m.id_producto, m.talla_individual)] = m.stock_resultante
    desync = 0
    for s in Stock.query.all():
        clave = (s.id_colegio, s.id_producto, s.talla_individual)
        if clave in ultimo_mov and (s.cantidad or 0) != (ultimo_mov[clave] or 0):
            desync += 1
            if desync <= 15:
                print(f"  colegio={s.id_colegio} prod={s.id_producto} T{s.talla_individual}: "
                      f"stock={s.cantidad} vs kardex={ultimo_mov[clave]}")
    print(f"  Total tallas desincronizadas: {desync} "
          f"(esperable: las ventas web y ediciones no pasan por el kardex — ver ARQUITECTURA.md §5.B)")
    hallazgos += desync

    # ── 6. Uniformes COMPLETOS vs suma de piezas ───────────────────────────
    seccion('6. Precio de uniforme COMPLETO vs suma de sus piezas')
    prod_por_codigo = {p.codigo: p for p in Producto.query.all() if p.codigo}
    colegios = {c.id_colegio: c.nombre for c in Colegio.query.all()}
    precios = defaultdict(dict)  # (id_colegio, id_producto) -> {talla_grupo: precio}
    for pr in PrecioColegio.query.all():
        precios[(pr.id_colegio, pr.id_producto)][pr.talla_grupo] = float(pr.precio_unitario)

    anomalias = 0
    for cod_uni, cod_piezas in COMBOS_UNIFORME.items():
        uni = prod_por_codigo.get(cod_uni)
        if not uni:
            continue
        piezas = [prod_por_codigo.get(c) for c in cod_piezas]
        if any(p is None for p in piezas):
            continue
        for id_col, nombre_col in colegios.items():
            tabla_uni = precios.get((id_col, uni.id_producto), {})
            for talla, precio_uni in tabla_uni.items():
                suma = 0
                completo = True
                for pieza in piezas:
                    v = precios.get((id_col, pieza.id_producto), {}).get(talla)
                    if v is None:
                        completo = False
                        break
                    suma += v
                if not completo:
                    continue
                dif = precio_uni - suma
                if dif > 0:  # el paquete cuesta MÁS que las piezas → anomalía
                    anomalias += 1
                    print(f"  ⚠ {nombre_col} {cod_uni} T{talla}: completo={precio_uni:.0f} "
                          f"> suma piezas={suma:.0f} (dif +{dif:.0f})")
    print(f"  Anomalías (completo más caro que las piezas): {anomalias}")
    print("  Nota: descuentos (completo < suma) se consideran intencionales y no se listan.")
    hallazgos += anomalias

    # ── 7. Reservas activas ya vencidas ────────────────────────────────────
    seccion('7. Reservas en estado activa pero ya vencidas')
    vencidas = Reserva.query.filter(
        Reserva.estado == 'activa',
        Reserva.fecha_expiracion < datetime.utcnow()).count()
    print(f"  Total: {vencidas} (el daemon de run.py las limpia cada 60 s; >0 sostenido = daemon caído)")

    print(f"\n{'═' * 70}\nRESUMEN: {hallazgos} hallazgos que requieren revisión.\n"
          f"Este script NO modificó nada. Las correcciones se deciden una a una.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        diagnosticar()
