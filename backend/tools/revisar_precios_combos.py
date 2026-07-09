"""
RALOZ COL S.A.S — Revisión del modelo de precios de uniformes completos (#4).

El `diagnostico_datos.py` ya detecta anomalías donde el combo cuesta MÁS que la
suma de piezas. Este script va un paso más allá:

  - Para cada (colegio, uniforme_completo, talla_grupo) calcula:
      * precio actual
      * suma de piezas individuales
      * descuento actual implícito = (1 - precio/suma)
  - Si el descuento varía más de 3 puntos porcentuales entre colegios para el
    mismo uniforme, los marca como "INCONSISTENTE" y propone un precio
    normalizado con la MEDIANA del descuento.
  - Si el uniforme ya está descontado parejo, lo marca como "OK".
  - NO MODIFICA NADA. Solo imprime un reporte y (opcional) exporta CSV.

USO:
    cd backend
    python tools/revisar_precios_combos.py
    python tools/revisar_precios_combos.py --csv-dir backups
    python tools/revisar_precios_combos.py --umbral-pp 3       # 3 puntos de tolerancia
    python tools/revisar_precios_combos.py --descuento-meta 0.15   # proponer 15% de dto
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app  # noqa: E402
from sqlalchemy import text  # noqa: E402

# Reusa los mapeos del diagnóstico para no duplicar verdad en dos archivos
from tools.diagnostico_datos import COMBOS_UNIFORME  # noqa: E402

# UTF-8 en consola: evita UnicodeEncodeError con ─/emojis en Windows (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
except Exception:
    pass


def parsear_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", default=None)
    ap.add_argument("--umbral-pp", type=float, default=3.0,
                    help="Tolerancia en puntos porcentuales para considerar OK (3 = 3%)")
    ap.add_argument("--descuento-meta", type=float, default=None,
                    help="Si lo pasas, propone un PRECIO sugerido con ese descuento "
                         "(ej: 0.15 = 15% dto sobre la suma de piezas)")
    return ap.parse_args()


def fmt_cop(v):
    if v is None:
        return "-"
    try:
        return "$" + f"{float(v):,.0f}".replace(",", ".")
    except Exception:
        return str(v)


def seccion(t):
    print()
    print("═" * 78)
    print(f"  {t}")
    print("═" * 78)


def tabla_md(headers, filas):
    if not filas:
        print("| (vacío) |")
        return
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for fila in filas:
        print("| " + " | ".join(str(c) if c is not None else "-" for c in fila) + " |")


def obtener_datos(db):
    """Pull:
        productos  {codigo → (id_producto, nombre, tipo)}
        precios    {(id_colegio, id_producto, talla_grupo) → precio_unitario}
        colegios   {id_colegio → nombre}
    """
    prod_rows = db.session.execute(text("""
        SELECT id_producto, codigo, nombre, tipo FROM productos
    """)).mappings().all()
    productos = {r["codigo"]: (r["id_producto"], r["nombre"], r["tipo"])
                 for r in prod_rows if r["codigo"]}
    col_rows = db.session.execute(text("""
        SELECT id_colegio, nombre FROM colegios
    """)).mappings().all()
    colegios = {r["id_colegio"]: r["nombre"] for r in col_rows}
    prec_rows = db.session.execute(text("""
        SELECT id_colegio, id_producto, talla_grupo, precio_unitario
        FROM precios_colegio
    """)).mappings().all()
    precios = {(r["id_colegio"], r["id_producto"], r["talla_grupo"]):
               float(r["precio_unitario"] or 0) for r in prec_rows}
    return productos, colegios, precios


def diff_para(colegios, id_col, id_prod, talla_grupo, precios):
    """Si tengo la combinación completa, devuelve precio del combo y suma
    de piezas, en otro caso (None, None)."""
    precio = precios.get((id_col, id_prod, talla_grupo))
    if precio is None:
        return None, None
    # Buscar piezas: COMBOS_UNIFORME tiene códigos; mapeo a id_producto
    return None, None  # se llena fuera, con acceso a la tabla


def escribir_csv(path, headers, filas):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(filas)


def main():
    args = parsear_args()
    csv_dir = Path(args.csv_dir) if args.csv_dir else None
    print(f"# Revisión precios uniformes completos RALOZ · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Tolerancia OK: descuento consistente dentro de ±{args.umbral_pp} puntos porcentuales")

    app = create_app()
    with app.app_context():
        from app import db  # instancia SQLAlchemy del backend
        productos, colegios, precios = obtener_datos(db)

        # Construir la matriz: por cada uniforme + talla_grupo,
        # {colegio_id → {precio_combo, suma_piezas, descuento_pct}}
        matriz = defaultdict(lambda: defaultdict(dict))    # [(combo_id, talla)] → {colegio → datos}

        for cod_uni, codigos_piezas in COMBOS_UNIFORME.items():
            uni = productos.get(cod_uni)
            if not uni:
                print(f"[ADVERTENCIA] Producto uniforme {cod_uni} no existe")
                continue
            id_uni = uni[0]
            piezas = []
            for cod in codigos_piezas:
                p = productos.get(cod)
                if not p:
                    print(f"[ADVERTENCIA] Pieza {cod} del combo {cod_uni} no existe")
                    piezas = []
                    break
                piezas.append(p)
            if not piezas:
                continue
            # Para cada colegio y talla_grupo en la que el uniforme tiene precio
            for (id_colegio, id_prod_uni, tg_uni), prec_combo in precios.items():
                if id_prod_uni != id_uni:
                    continue
                suma_piezas = 0.0
                completo = True
                for p in piezas:
                    prec_pieza = precios.get((id_colegio, p[0], tg_uni))
                    if prec_pieza is None:
                        completo = False
                        break
                    suma_piezas += prec_pieza
                if not completo:
                    continue
                descuento = (1 - prec_combo / suma_piezas) * 100 if suma_piezas > 0 else 0
                matriz[(cod_uni, tg_uni)][id_colegio] = {
                    "precio_combo":    prec_combo,
                    "suma_piezas":     suma_piezas,
                    "descuento_pct":   descuento,
                    "uni_nombre":      uni[1],
                }

        if not matriz:
            print("\nSin datos suficientes para analizar.")
            return

        seccion("RESUMEN POR COMBO (descuento que se aplica hoy)")
        filas_resumen = []
        todas = []
        for (cod_uni, tg_uni), por_col in matriz.items():
            descuentos = [v["descuento_pct"] for v in por_col.values()]
            min_d, max_d = min(descuentos), max(descuentos)
            dispersion = max_d - min_d
            mediana = statistics.median(descuentos) if descuentos else 0
            status = "OK" if dispersion <= args.umbral_pp else "INCONSISTENTE"
            for id_col, v in por_col.items():
                todas.append({
                    "combo":          cod_uni,
                    "talla_grupo":    tg_uni,
                    "colegio":        colegios.get(id_col, f"#{id_col}"),
                    "precio_combo":   v["precio_combo"],
                    "suma_piezas":    v["suma_piezas"],
                    "descuento_pct":  v["descuento_pct"],
                    "dispersion_pp":  dispersion,
                    "mediana_pp":     mediana,
                    "status":         status,
                })
                filas_resumen.append([
                    status,
                    cod_uni,
                    tg_uni,
                    colegios.get(id_col, f"#{id_col}"),
                    fmt_cop(v["precio_combo"]),
                    fmt_cop(v["suma_piezas"]),
                    f"{v['descuento_pct']:.1f}%",
                ])
        tabla_md(["Status", "Combo", "Talla", "Colegio", "Precio combo", "Suma piezas", "Dto. %"], filas_resumen)

        # Detalle solo de INCONSISTENTES
        inconsistentes = [x for x in todas if x["status"] == "INCONSISTENTE"]
        if inconsistentes:
            seccion(f"INCONSISTENCIAS ({len(inconsistentes)} combos con descuentos que difieren)")
            inconsistentes.sort(key=lambda r: -r["dispersion_pp"])
            tabla_md(
                ["Combo", "Talla", "Colegio", "Precio", "Dto.%", "Mediana(dto%)", "Diff vs mediana (pp)"],
                [
                    [r["combo"], r["talla_grupo"], r["colegio"],
                     fmt_cop(r["precio_combo"]),
                     f"{r['descuento_pct']:.1f}%",
                     f"{r['mediana_pp']:.1f}%",
                     f"{r['descuento_pct'] - r['mediana_pp']:+.1f}"]
                    for r in inconsistentes
                ],
                )

            # Si pidió descuento_meta, propongo el precio "uniforme"
            if args.descuento_meta is not None:
                seccion(f"PROPUESTA con descuento objetivo {args.descuento_meta*100:.0f}% sobre la suma de piezas")
                filas_prop = []
                # agrupar por combo para que la propuesta tenga sentido
                props = defaultdict(list)
                for r in inconsistentes:
                    key = (r["combo"], r["talla_grupo"])
                    nuevo_precio = round(r["suma_piezas"] * (1 - args.descuento_meta))
                    diff = nuevo_precio - r["precio_combo"]
                    props[key] = (nuevo_precio, r["precio_combo"], diff, r["colegio"], r["suma_piezas"])
                for (combo, tg), (nuevo_precio, precio_actual, diff, colegio, suma) in sorted(props.items()):
                    filas_prop.append([
                        combo, tg, colegio,
                        fmt_cop(precio_actual), fmt_cop(suma),
                        fmt_cop(nuevo_precio),
                        f"{diff:+,}" if diff else "ok",
                    ])
                tabla_md(
                    ["Combo", "Talla", "Colegio", "Actual", "Suma", "Propuesto", "Δ"],
                    filas_prop,
                )
                print()
                print("NOTA: estos precios son solo una guía. Aplicar requiere:")
                print("  1. Decidir el descuento objetivo (sugerido: la MEDIANA actual)")
                print("  2. Aplicar en el panel admin > Productos > Precios por colegio")
                print("  3. Validar con el cliente si conviene vender al precio actual mientras tanto")

        if csv_dir:
            escribir_csv(
                csv_dir / f"revision_precios_combos_{datetime.now().date().isoformat()}.csv",
                ["status", "combo", "talla_grupo", "colegio",
                 "precio_combo", "suma_piezas", "descuento_pct",
                 "mediana_pp", "dispersion_pp"],
                [[r["status"], r["combo"], r["talla_grupo"], r["colegio"],
                  r["precio_combo"], r["suma_piezas"], round(r["descuento_pct"], 2),
                  round(r["mediana_pp"], 2), round(r["dispersion_pp"], 2)]
                 for r in todas],
            )
            print(f"\nCSV: backups/revision_precios_combos_<fecha>.csv")

        print("\n# Fin.")


if __name__ == "__main__":
    main()
