"""
Limpieza de DATOS DE PRUEBA antes de lanzar a producción.

⚠️  LO CORRE EL DUEÑO con su DATABASE_URL. Borra pedidos web de prueba (y sus
facturas/pagos/fabricación) creados desde una fecha, y opcionalmente reinicia
el consecutivo de facturación para arrancar limpio.

SEGURO POR DEFECTO: sin --confirm solo MUESTRA lo que haría (no borra nada).

  # 1) SIEMPRE haz un backup primero:
  python backup_db.py

  # 2) Previsualiza (no borra):
  DATABASE_URL="postgresql://..." python limpiar_datos_prueba.py --desde 2026-06-10

  # 3) Si el listado es correcto, ejecuta de verdad:
  DATABASE_URL="postgresql://..." python tools/limpiar_datos_prueba.py --desde 2026-06-10 --confirm --reset-serie
"""
import argparse
import os
import sys
from datetime import datetime, date

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# El script vive en tools/; el paquete `app` está un nivel arriba (backend/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    PedidoWeb, Factura, FacturaDetalle, Pago,
    PedidoFabricacion, SerieFacturacion,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desde', required=True, help='Borra pedidos web creados en/después de esta fecha (YYYY-MM-DD)')
    ap.add_argument('--confirm', action='store_true', help='Ejecuta de verdad (sin esto solo previsualiza)')
    ap.add_argument('--reset-serie', action='store_true', help='Reinicia el consecutivo de facturación a 0')
    args = ap.parse_args()

    try:
        corte = datetime.strptime(args.desde, '%Y-%m-%d')
    except ValueError:
        print('Fecha inválida. Usa YYYY-MM-DD'); sys.exit(2)

    app = create_app()
    with app.app_context():
        pedidos = PedidoWeb.query.filter(PedidoWeb.fecha_creacion >= corte) \
            .order_by(PedidoWeb.fecha_creacion).all()

        print(f"\nPedidos web creados desde {args.desde}: {len(pedidos)}\n")
        factura_ids = []
        for p in pedidos:
            fac = f" | factura {p.id_factura}" if p.id_factura else ""
            print(f"  {p.referencia}  {p.fecha_creacion}  {p.nombre_cliente}  ${p.total:,.0f}  [{p.estado}]{fac}")
            if p.id_factura:
                factura_ids.append(p.id_factura)

        if not args.confirm:
            print("\n(MODO PREVISUALIZACIÓN — no se borró nada. Agrega --confirm para ejecutar.)")
            if args.reset_serie:
                serie = SerieFacturacion.query.filter_by(activa=True).first()
                print(f"  [reset-serie] consecutivo actual: {serie.consecutivo_actual if serie else 'sin serie'} → 0")
            return

        # ── BORRADO REAL ──
        borr_pagos = borr_det = borr_fab = borr_fac = 0
        for fid in factura_ids:
            borr_pagos += Pago.query.filter_by(id_factura=fid).delete(synchronize_session=False)
            borr_det += FacturaDetalle.query.filter_by(id_factura=fid).delete(synchronize_session=False)
        for p in pedidos:
            borr_fab += PedidoFabricacion.query.filter_by(id_pedido_web=p.id_pedido).delete(synchronize_session=False)
        # quitar el vínculo y borrar pedidos, luego facturas
        for p in pedidos:
            p.id_factura = None
        db.session.flush()
        for p in pedidos:
            db.session.delete(p)
        db.session.flush()
        for fid in factura_ids:
            f = db.session.get(Factura, fid)
            if f:
                db.session.delete(f)
                borr_fac += 1

        if args.reset_serie:
            serie = SerieFacturacion.query.filter_by(activa=True).first()
            if serie:
                serie.consecutivo_actual = 0
                print(f"  [reset-serie] consecutivo reiniciado a 0")

        db.session.commit()
        print(f"\n✅ Borrado: {len(pedidos)} pedidos, {borr_fac} facturas, "
              f"{borr_det} líneas, {borr_pagos} pagos, {borr_fab} fabricaciones.")
        print("   NOTA: el stock descontado por las pruebas NO se restaura — ajústalo en el panel.")


if __name__ == '__main__':
    main()
