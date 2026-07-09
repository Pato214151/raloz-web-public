"""
RALOZ COL S.A.S — Análisis de ventas + recomendación de fabricación para
preparar la temporada de regreso a clases.

USO:
    cd backend
    python tools/analisis_temporada.py                                # últimos 12 meses
    python tools/analisis_temporada.py --desde 2025-08-01 --hasta 2026-06-30
    python tools/analisis_temporada.py --csv-dir backups/
    python tools/analisis_temporada.py --escenarios "1.0,1.15,1.30"   # conservador/base/optimista

LEE LA BD (solo SELECT). NO TOCA NADA.

Salidas (en stdout, en markdown) y, si pasas --csv-dir, los CSV también:

  1. Panorama general         (KPIs, ventas por canal y colegio)
  2. Top prendas/tallas       (colegio × producto × talla)
  3. Inventario actual        (stock por colegio × producto × talla)
  4. Recomendación fabricación (3 escenarios con colchón)
  5. Auditoría rápida         (consistencia con el último diagnóstico)

BONUS: cruzamos con .last_state.json del weekly maintenance para reportar
si las 2 facturas descuadradas detectadas previamente siguen ahí.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# ── path bootstrap para ejecutar como script standalone ──────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app  # noqa: E402

from app.models import (  # noqa: E402
    Colegio, Producto, PrecioColegio,
    Stock, Reserva,
    PedidoWeb, Factura, Pago, PedidoFabricacion,
)
from app.utils.tallas import expandir_grupo_para_producto  # noqa: E402
from sqlalchemy import func, text  # noqa: E402

# UTF-8 en consola: evita UnicodeEncodeError con ═/emojis en Windows (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
except Exception:
    pass

ESTADO_FILE_DEFAULT = Path(__file__).resolve().parents[1] / "backups" / ".last_state.json"


# ────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────

def parsear_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default=None, help="YYYY-MM-DD (default: 1 año atrás)")
    ap.add_argument("--hasta", default=None, help="YYYY-MM-DD (default: hoy)")
    ap.add_argument("--csv-dir", default=None, help="Carpeta donde escribir CSVs (opcional)")
    ap.add_argument("--escenarios", default="1.0,1.15,1.30",
                    help="Multiplicadores separados por coma, en orden (ej '1.0,1.15,1.30')")
    ap.add_argument("--estado", default=str(ESTADO_FILE_DEFAULT),
                    help="Path al .last_state.json del weekly maintenance")
    ap.add_argument("--top", type=int, default=30, help="N de filas a imprimir en Top")
    return ap.parse_args()


def fmt_cop(v) -> str:
    if v is None:
        return "-"
    try:
        return "$" + f"{float(v):,.0f}".replace(",", ".")
    except Exception:
        return str(v)


def imprimir_seccion(titulo: str) -> None:
    """Borde estilo markdown para stdout."""
    print()
    print("═" * 78)
    print(f"  {titulo}")
    print("═" * 78)


def tabla_md(headers, filas, limite=None) -> None:
    if limite:
        filas = filas[:limite]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for fila in filas:
        print("| " + " | ".join(str(c) if c is not None else "-" for c in fila) + " |")


def escribir_csv(path: Path, headers, filas) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(filas)


# ────────────────────────────────────────────────────────────────────
# QUERIES
# ────────────────────────────────────────────────────────────────────

def kpis_generales(db, desde: date, hasta: date) -> dict:
    """KPI global: pedidos web, facturas POS, abonos."""
    # Ventas web (pedidos pagados)
    res = db.session.execute(text("""
        SELECT COUNT(*) AS pedidos_pagados,
               COALESCE(SUM(total), 0)      AS ingresos_web
        FROM pedidos_web
        WHERE estado = 'pagado'
          AND fecha_pago >= :desde
          AND fecha_pago <  :hasta
    """), {"desde": desde, "hasta": hasta}).mappings().first()
    pedidos_pagados = res["pedidos_pagados"] or 0
    ingresos_web = float(res["ingresos_web"] or 0)

    # Ventas POS (facturas locales no anuladas)
    res = db.session.execute(text("""
        SELECT COUNT(*)         AS facturas,
               COALESCE(SUM(total), 0) AS ingresos_pos
        FROM facturas
        WHERE estado != 'ANULADA'
          AND fecha_factura >= :desde
          AND fecha_factura <  :hasta
    """), {"desde": desde, "hasta": hasta}).mappings().first()
    n_facturas = res["facturas"] or 0
    ingresos_pos = float(res["ingresos_pos"] or 0)

    # Abonos cobrados (todos los pagos del periodo)
    res = db.session.execute(text("""
        SELECT COALESCE(SUM(valor), 0) AS abonos
        FROM pagos
        WHERE fecha_pago >= :desde
          AND fecha_pago <  :hasta
    """), {"desde": desde, "hasta": hasta}).mappings().first()
    abonos = float(res["abonos"] or 0)

    # Unidades POS (factura_detalle.cantidad) — para completar panorama
    res = db.session.execute(text("""
        SELECT COALESCE(SUM(fd.cantidad), 0) AS unidades_pos
        FROM facturas f
        JOIN factura_detalle fd ON fd.id_factura = f.id_factura
        WHERE f.estado != 'ANULADA'
          AND f.fecha_factura >= :desde
          AND f.fecha_factura <  :hasta
    """), {"desde": desde, "hasta": hasta}).mappings().first()
    unidades_pos = int(res["unidades_pos"] or 0)

    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "pedidos_web_pagados": pedidos_pagados,
        "ingresos_web": ingresos_web,
        "facturas_pos": n_facturas,
        "ingresos_pos": ingresos_pos,
        "ingresos_total": ingresos_web + ingresos_pos,
        "abonos_cobrados": abonos,
        "unidades_pos":    unidades_pos,
    }


def ventas_por_canal_y_colegio(db, desde: date, hasta: date) -> list:
    """Cruzado de canales: web (por colegio) + POS (por colegio via factura.id_colegio).
    IMPORTANTE: SUM(f.total) se calcula SIN join a factura_detalle para no
    multiplicar por el número de líneas de cada factura (join inflaría la suma
    tantas veces como líneas tenga)."""
    # Web
    res_web = db.session.execute(text("""
        SELECT id_colegio, nombre_colegio,
               COUNT(*) AS pedidos,
               SUM(total) AS ingresos
        FROM pedidos_web
        WHERE estado = 'pagado'
          AND fecha_pago >= :desde
          AND fecha_pago <  :hasta
        GROUP BY id_colegio, nombre_colegio
        ORDER BY ingresos DESC
    """), {"desde": desde, "hasta": hasta}).mappings().all()

    # POS por colegio (una sola subquery para evitar duplicación por JOIN)
    res_pos = db.session.execute(text("""
        WITH facturas_pos AS (
            SELECT id_colegio, total
            FROM facturas
            WHERE estado != 'ANULADA'
              AND fecha_factura >= :desde
              AND fecha_factura <  :hasta
        ),
        unidades_pos AS (
            SELECT f.id_colegio, SUM(fd.cantidad) AS unidades
            FROM facturas f
            JOIN factura_detalle fd ON fd.id_factura = f.id_factura
            WHERE f.estado != 'ANULADA'
              AND f.fecha_factura >= :desde
              AND f.fecha_factura <  :hasta
            GROUP BY f.id_colegio
        )
        SELECT c.id_colegio,
               c.nombre AS colegio,
               COUNT(fp.total) AS facturas,
               COALESCE(SUM(fp.total), 0) AS ingresos,
               COALESCE(up.unidades, 0)   AS unidades
        FROM colegios c
        JOIN facturas_pos fp ON fp.id_colegio = c.id_colegio
        LEFT JOIN unidades_pos up ON up.id_colegio = c.id_colegio
        GROUP BY c.id_colegio, c.nombre, up.unidades
        ORDER BY ingresos DESC
    """), {"desde": desde, "hasta": hasta}).mappings().all()

    out = []
    for r in res_web:
        cn = r["nombre_colegio"] or (f"colegio#{r['id_colegio']}" if r["id_colegio"] else "s/c")
        out.append({"canal": "Web", "colegio": cn, "cantidad": r["pedidos"], "ingresos": float(r["ingresos"] or 0), "unidades": None})
    for r in res_pos:
        out.append({"canal": "POS", "colegio": r["colegio"], "cantidad": int(r["facturas"]), "ingresos": float(r["ingresos"]), "unidades": int(r["unidades"] or 0)})
    return out


def expandir_venta_items(db, desde: date, hasta: date):
    """
    Devuelve lista plana de filas con la llave de fabricación:
        (colegio_id, colegio, id_producto, producto, tipo, talla_individual,
         unidades, ingresos)
    **Usa `factura_detalle` (POS) como fuente principal** — los pedidos_web
    son muy pocos para tener peso estadístico. Si la web pesa más en el
    futuro, agregar una UNION aquí.
    """
    filas = []
    q = text("""
        SELECT f.id_colegio, c.nombre    AS colegio_nombre,
               fd.id_producto, p.nombre   AS producto, p.tipo,
               fd.talla_individual,
               fd.cantidad, fd.precio_unitario
        FROM facturas f
        JOIN colegios c         ON c.id_colegio = f.id_colegio
        JOIN factura_detalle fd  ON fd.id_factura = f.id_factura
        JOIN productos p        ON p.id_producto = fd.id_producto
        WHERE f.estado != 'ANULADA'
          AND f.fecha_factura >= :desde
          AND f.fecha_factura <  :hasta
    """)
    for r in db.session.execute(q, {"desde": desde, "hasta": hasta}).mappings():
        cant = int(r["cantidad"] or 0)
        if cant <= 0:
            continue
        precio = float(r["precio_unitario"] or 0)
        filas.append({
            "colegio_id":       r["id_colegio"],
            "colegio":          r["colegio_nombre"],
            "id_producto":      r["id_producto"],
            "producto":         r["producto"],
            "tipo":             r["tipo"] or "",
            "talla_individual": r["talla_individual"],
            "unidades":         cant,
            "ingresos":         cant * precio,
        })
    return filas


def top_prendas_tallas(filas_expandidas, top=30):
    """Agrupa por colegio+producto+talla_individual y suma unidades/ingresos."""
    agg = {}
    for f in filas_expandidas:
        k = (f["colegio_id"], f["colegio"], f["id_producto"], f["producto"],
             f["talla_individual"])
        if k not in agg:
            agg[k] = {"unidades": 0.0, "ingresos": 0.0}
        agg[k]["unidades"] += f["unidades"]
        agg[k]["ingresos"] += f["ingresos"]
    out = []
    for (cid, cnombre, ip, prod, ti), v in agg.items():
        out.append({
            "colegio":       cnombre or f"colegio#{cid}",
            "id_producto":   ip,
            "producto":      prod,
            "talla":         ti,
            "unidades":      int(round(v["unidades"])),
            "ingresos":      round(v["ingresos"], 0),
        })
    out.sort(key=lambda r: (-r["unidades"], r["colegio"], r["producto"], r["talla"]))
    return out


def inventario_actual(db) -> list:
    """Stock por colegio × producto × talla. Devuelve también las tallas con
    stock = 0 para que la tabla sea completa."""
    rows = db.session.execute(text("""
        SELECT s.id_colegio, c.nombre AS colegio,
               s.id_producto, p.nombre AS producto, p.tipo,
               s.talla_individual, s.cantidad
        FROM stock s
        JOIN colegios c   ON c.id_colegio = s.id_colegio
        JOIN productos p  ON p.id_producto = s.id_producto
        ORDER BY c.nombre, p.nombre, s.talla_individual
    """)).mappings().all()
    out = []
    for r in rows:
        out.append({
            "colegio":   r["colegio"],
            "id_producto": r["id_producto"],
            "producto":  r["producto"],
            "tipo":      r["tipo"] or "",
            "talla":     r["talla_individual"],
            "stock":     int(r["cantidad"] or 0),
        })
    return out


def recomendaciones_fabricacion(filas_expandidas, inventario, escenarios_factors):
    """
    Por cada (colegio, producto, talla_individual):
      - vendidas_12m = SUM(unidades) de filas_expandidas (1 año)
      - stock_actual  = inventario en esa clave
      - recomendado_<factor>  = vendidas_12m * factor - stock_actual (mínimo 0)
    """
    # suma por (colegio, id_producto, talla)
    demanda = {}
    for f in filas_expandidas:
        k = (f["colegio"], f["id_producto"], f["producto"], f["tipo"], f["talla_individual"])
        demanda.setdefault(k, 0.0)
        demanda[k] += f["unidades"]

    stock_lookup = {}
    for s in inventario:
        k = (s["colegio"], s["id_producto"], s["producto"], s["talla"])
        stock_lookup[k] = stock_lookup.get(k, 0) + s["stock"]

    filas = []
    for k, vd in demanda.items():
        cnombre, ip, prod, tipo, ti = k
        stk = stock_lookup.get(k, 0)
        recomendaciones = {}
        for label, factor in escenarios_factors.items():
            rec = max(0.0, vd * factor - stk)
            recomendaciones[label] = int(round(rec))
        filas.append({
            "colegio":   cnombre,
            "id_producto": ip,
            "producto":  prod,
            "tipo":      tipo,
            "talla":     ti,
            "vendidas_12m": round(vd, 1),
            "stock":     stk,
            **recomendaciones,
        })
    # Ordenar por demanda descendente (mayor urgencia primero)
    filas.sort(key=lambda r: (-r["vendidas_12m"], r["colegio"], r["producto"], r["talla"]))
    return filas


def cargar_estado_mantenimiento(path: Path):
    if not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────

def main():
    args = parsear_args()
    hoy = date.today()
    hasta = date.fromisoformat(args.hasta) if args.hasta else hoy
    desde = date.fromisoformat(args.desde) if args.desde else (hasta - timedelta(days=365))
    csv_dir = Path(args.csv_dir) if args.csv_dir else None

    factores = [float(x) for x in args.escenarios.split(",") if x.strip()]
    if len(factores) == 1:
        factores = [factores[0], round(factores[0] + 0.15, 2), round(factores[0] + 0.30, 2)]
    if len(factores) < 3:
        factores = (factores + [1.0, 1.15, 1.30])[:3]
    escenarios_labels = {f"rec_f{f:.2f}".replace(".", ""): f for f in factores}

    print(f"# Análisis RALOZ COL S.A.S · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Ventana analizada: {desde.isoformat()} → {hasta.isoformat()} ({ (hasta - desde).days } días)")
    print(f"# Escenarios: " + ", ".join([f"{lab}={fac:.2f}×demanda" for lab, fac in escenarios_labels.items()]))

    app = create_app()
    with app.app_context():
        db = app.extensions['migrate'].db if 'migrate' in app.extensions else __import__('app.db', fromlist=['db']).db

        # ── 1. KPIs ──────────────────────────────────────────────
        kpis = kpis_generales(db, desde, hasta)
        imprimir_seccion("1) PANORAMA GENERAL")
        tabla_md(
            ["Métrica", "Valor"],
            [
                ["Período",                  f"{kpis['desde']} → {kpis['hasta']}"],
                ["Pedidos web pagados",      kpis["pedidos_web_pagados"]],
                ["Ingresos (web)",           fmt_cop(kpis["ingresos_web"])],
                ["Facturas POS (no anuladas)", kpis["facturas_pos"]],
                ["Ingresos (POS)",           fmt_cop(kpis["ingresos_pos"])],
                ["Ingresos TOTALES",         fmt_cop(kpis["ingresos_total"])],
                ["Abonos cobrados en período", fmt_cop(kpis["abonos_cobrados"])],
            ],
        )

        # ── 2. Ventas por canal y colegio ───────────────────────
        imprimir_seccion("2) INGRESOS POR CANAL Y COLEGIO")
        canal_filas = []
        for r in ventas_por_canal_y_colegio(db, desde, hasta):
            unidad_label = (
                f"{r['cantidad']} facturas" if r["canal"] == "POS"
                else f"{r['cantidad']} pedidos"
            )
            extras = ""
            if r.get("unidades"):
                extras = f" · {r['unidades']} unidades"
            canal_filas.append([
                f"{r['canal']} · {r['colegio']}",
                unidad_label + extras,
                fmt_cop(r["ingresos"]),
            ])
        canal_filas.append([
            "**TOTAL**",
            f"{kpis['pedidos_web_pagados']} web + {kpis['facturas_pos']} POS = "
            f"{kpis['pedidos_web_pagados'] + kpis['facturas_pos']} (· {kpis['unidades_pos']} u. POS)",
            fmt_cop(kpis["ingresos_total"]),
        ])
        tabla_md(["Canal · Colegio", "Cantidad", "Ingresos"], canal_filas)

        # ── 3. Top prendas × colegio × talla ────────────────────
        imprimir_seccion(f"3) TOP PRENDAS × COLEGIO × TALLA (Top {args.top})")
        filas_expandidas = expandir_venta_items(db, desde, hasta)
        top = top_prendas_tallas(filas_expandidas, top=args.top)
        tabla_md(
            ["Colegio", "Producto", "Talla", "Unidades (12m)", "Ingresos (12m)"],
            [[r["colegio"], r["producto"], r["talla"], r["unidades"], fmt_cop(r["ingresos"])] for r in top],
            limite=args.top,
        )
        if csv_dir:
            escribir_csv(csv_dir / f"top_prendas_{desde}_{hasta}.csv",
                         ["colegio", "id_producto", "producto", "talla", "unidades_12m", "ingresos_12m"],
                         [[r["colegio"], r["id_producto"], r["producto"], r["talla"], r["unidades"], r["ingresos"]]
                          for r in top])

        # ── 4. Inventario actual ────────────────────────────────
        imprimir_seccion("4) INVENTARIO ACTUAL POR COLEGIO (resumen)")
        inv = inventario_actual(db)
        # Total unidades en stock
        total_unidades = sum(s["stock"] for s in inv)
        # Items con stock bajo (< 5) y con stock 0
        bajos = [s for s in inv if 0 < s["stock"] < 5]
        ceros = [s for s in inv if s["stock"] == 0]
        tabla_md(
            ["Métrica", "Valor"],
            [
                ["Total SKUs en stock (colegio, producto, talla)", len(inv)],
                ["Unidades totales en stock", total_unidades],
                ["Items con stock BAJO (1–4 unidades)", len(bajos)],
                ["Items AGOTADOS (stock=0)", len(ceros)],
            ],
        )
        if bajos:
            print("\nItems con stock bajo (< 5):")
            tabla_md(
                ["Colegio", "Producto", "Talla", "Stock"],
                [[s["colegio"], s["producto"], s["talla"], s["stock"]] for s in bajos],
                limite=15,
            )
        if csv_dir:
            escribir_csv(csv_dir / f"inventario_actual.csv",
                         ["colegio", "id_producto", "producto", "tipo", "talla", "stock"],
                         [[s["colegio"], s["id_producto"], s["producto"], s["tipo"], s["talla"], s["stock"]]
                          for s in inv])

        # ── 5. Recomendaciones de fabricación ──────────────────
        imprimir_seccion("5) RECOMENDACIÓN DE FABRICACIÓN (3 escenarios)")
        print(f"# vendidos_12m = suma de unidades vendidas (último año, expandiendo grupo → talla individual)")
        print(f"# recomendado_X = vendidas_12m × factor − stock_actual  (mínimo 0)")
        print(f"# Si recomendado = 0, no fabricues de esa combinación (no hay demanda o el stock alcanza)")
        print()
        recos = recomendaciones_fabricacion(filas_expandidas, inv, escenarios_labels)
        tabla_md(
            ["Colegio", "Producto", "Talla", "Vendidas 12m", "Stock"] + [lbl for lbl in escenarios_labels],
            [
                [r["colegio"], r["producto"], r["talla"], r["vendidas_12m"], r["stock"]]
                + [r[lbl] for lbl in escenarios_labels]
                for r in recos
            ],
            limite=40,
        )
        total_rec = {lbl: sum(r[lbl] for r in recos) for lbl in escenarios_labels}
        print()
        print(f"TOTAL unidades a fabricar (suma todos los colegios y tallas): "
              + ", ".join([f"{lbl}={total_rec[lbl]}" for lbl in escenarios_labels]))
        if csv_dir:
            escribir_csv(
                csv_dir / f"recomendacion_fabricacion_{desde}_{hasta}.csv",
                ["colegio", "id_producto", "producto", "tipo", "talla",
                 "vendidas_12m", "stock"] + list(escenarios_labels.keys()),
                [[r["colegio"], r["id_producto"], r["producto"], r["tipo"], r["talla"],
                  r["vendidas_12m"], r["stock"]] + [r[lbl] for lbl in escenarios_labels]
                 for r in recos],
            )

        # ── 6. Bonus: cruzar con weekly maintenance ─────────────
        imprimir_seccion("6) AUDITORÍA (cruzado con weekly-maintenance)")
        estado = cargar_estado_mantenimiento(Path(args.estado))
        if estado:
            print(f"Último diagnóstico semanal: {estado.get('fecha', '?')}")
            print(f"  Total hallazgos: {estado.get('hallazgos', {}).get('total', '?')}")
            for k, v in (estado.get("hallazgos") or {}).items():
                if k in ("total", "__resumen_total__") or not isinstance(v, int):
                    continue
                print(f"    - {k}: {v}")
            print(f"  Backup OK: {estado.get('backup', {}).get('ok', '?')}")
            print(f"  Verificación tablas: {estado.get('backup', {}).get('verificacion_ok', '?')}")
        else:
            print(f"No hay estado previo ({args.estado}). Corre tools/maintenance.py para comenzar.")

    print("\n# Fin.")


if __name__ == "__main__":
    main()
