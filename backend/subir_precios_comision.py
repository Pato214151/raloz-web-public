"""
Sube TODOS los precios del catálogo un porcentaje parejo, para cubrir la comisión
de la pasarela de pago (MercadoPago 2,99% + $800) sin perder margen.

⚠️  LO CORRE EL DUEÑO con su DATABASE_URL. Modifica precios_colegio EN VIVO.

Regla:  nuevo = redondear_hacia_arriba( viejo * factor , al múltiplo )
        (por defecto: factor 1.035  ≈ +3,5%,  redondeo hacia arriba al $500)

SEGURO POR DEFECTO: sin --confirm solo MUESTRA la tabla viejo→nuevo (no guarda).

  # 1) SIEMPRE backup primero:
  python backup_db.py

  # 2) Previsualiza (no toca nada):
  DATABASE_URL="postgresql://..." python subir_precios_comision.py

  # 3) Si la tabla se ve bien, aplica de verdad:
  DATABASE_URL="postgresql://..." python subir_precios_comision.py --confirm
"""
import argparse
import csv
import math
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import create_app, db
from app.models import PrecioColegio, Colegio, Producto


def subir(viejo, factor, redondeo):
    """nuevo precio = viejo*factor redondeado HACIA ARRIBA al múltiplo `redondeo`."""
    objetivo = viejo * factor
    return int(math.ceil(objetivo / redondeo) * redondeo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--factor', type=float, default=1.035,
                    help='Multiplicador (1.035 = +3,5%%). Por defecto 1.035')
    ap.add_argument('--redondeo', type=int, default=500,
                    help='Múltiplo de redondeo hacia arriba. Por defecto 500')
    ap.add_argument('--confirm', action='store_true',
                    help='Aplica de verdad (sin esto solo previsualiza)')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        colegios = {c.id_colegio: c.nombre for c in Colegio.query.all()}
        productos = {p.id_producto: p.nombre for p in Producto.query.all()}

        precios = PrecioColegio.query.order_by(
            PrecioColegio.id_colegio, PrecioColegio.id_producto, PrecioColegio.talla_grupo
        ).all()

        print(f"\nFactor: x{args.factor}  ({(args.factor-1)*100:+.1f}%)   "
              f"Redondeo: hacia arriba al ${args.redondeo:,}\n")
        print(f"{'COLEGIO':<12} {'PRODUCTO':<28} {'TALLA':<7} {'VIEJO':>10} {'NUEVO':>10}  {'Δ':>8}")
        print('-' * 80)

        # Respaldo CSV de los precios actuales (por si toca revertir)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'respaldo_precios_{stamp}.csv'
        cambios = []
        col_actual = None
        for p in precios:
            nuevo = subir(p.precio_unitario, args.factor, args.redondeo)
            cambios.append((p, nuevo))
            if p.id_colegio != col_actual:
                col_actual = p.id_colegio
                print()
            print(f"{colegios.get(p.id_colegio,'?'):<12} "
                  f"{productos.get(p.id_producto,'?')[:28]:<28} "
                  f"{p.talla_grupo:<7} {p.precio_unitario:>10,.0f} {nuevo:>10,} "
                  f"{nuevo-p.precio_unitario:>+8,.0f}")

        print('-' * 80)
        print(f"Total de precios: {len(cambios)}")

        if not args.confirm:
            print("\n(MODO PREVISUALIZACIÓN — no se guardó nada. Agrega --confirm para aplicar.)")
            return

        # ── APLICAR ──
        with open(backup_path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['id_precio', 'id_colegio', 'id_producto', 'talla_grupo', 'precio_viejo'])
            for p, _ in cambios:
                w.writerow([p.id_precio, p.id_colegio, p.id_producto, p.talla_grupo, p.precio_unitario])
        print(f"\nRespaldo de precios anteriores: {backup_path}")

        for p, nuevo in cambios:
            p.precio_unitario = nuevo
        db.session.commit()
        print(f"✅ {len(cambios)} precios actualizados en la base de datos.")
        print("   Siguiente paso: regenerar la tienda con  node tools/sync_catalogo.mjs --write")


if __name__ == '__main__':
    main()
