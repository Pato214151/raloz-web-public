"""
RALOZ COL S.A.S — Alertas de stock bajo (proyecto #7).

Detecta combinaciones (colegio, producto, talla_individual) cuya cantidad
está por debajo de un umbral configurable, ANTES de que se agoten del todo.
Complementa tools/analisis_temporada.py: el análisis mira "qué fabricar"
(post-temporada), este mira "qué vas a necesitar la próxima semana".

Usa ventas reales (últimos 90 días) para calcular velocidad y dar
prioridad: si vendes 10 unidades/mes y te quedan 4, te avisa antes que
si vendes 0.5 unidades/mes y te quedan 4 (esos los cubre el análisis).

USO:
    cd backend
    python tools/alertas_stock.py                              # umbral default (5)
    python tools/alertas_stock.py --umbral 8                   # más estricto
    python tools/alertas_stock.py --umbral 3 --csv-dir backups # CSV exportable
    python tools/alertas_stock.py --no-notify                  # sin email

ENV (opcional, leido del .env o del entorno):
    MAINT_STOCK_UMBRAL     default del umbral si no pasas --umbral
    MAINT_STOCK_VENTANA    dias a mirar hacia atrás (defecto 90)

CRITERIO DE UMBRAL (lo que dispara alerta):

  CRITICA  agotado (stock=0) SI se vendió algo en los últimos 90 días
  CRITICA  semanas_restantes < 4 (con velocidad > 0)
  ALTA     semanas_restantes < 8
  MEDIA    stock <= umbral Y sin rotación
  BAJA     stock <= umbral Y sin ventas (no aparece en alertas — solo
           en el reporte total de "items en stock bajo")

NO TOCA LA BD (solo SELECT). Notifica por email solo si hay alertas
CRÍTICAS nuevas vs la corrida anterior.

Salida: stdout en markdown + opcionalmente CSV en backups/.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app  # noqa: E402
from sqlalchemy import text  # noqa: E402

from tools.notifier import enviar_email  # noqa: E402

STATE_FILE = Path(__file__).resolve().parents[1] / "backups" / ".stock_alerts_state.json"
BACKEND = STATE_FILE.parent.parent  # backend/


# ────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────

def parsear_args(argv: list | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--umbral", type=int, default=None,
                    help="Stock <= N dispara alerta (default: $MAINT_STOCK_UMBRAL o 5)")
    ap.add_argument("--ventana", type=int, default=None,
                    help="Días hacia atrás para calcular velocidad (default: 90)")
    ap.add_argument("--csv-dir", default=None,
                    help="Carpeta donde escribir el CSV con las alertas")
    ap.add_argument("--no-notify", action="store_true",
                    help="No enviar email (imprime el cuerpo)")
    return ap.parse_args(argv)


def _parsear_args(argv):  # shim
    return parsear_args(argv)


def leer_env(nombre: str, default) -> str:
    """Lee del entorno o del .env del backend (sin librerías)."""
    val = os.getenv(nombre, "").strip()
    if val:
        return val
    env_file = BACKEND / ".env"
    if env_file.exists():
        for ln in env_file.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith(f"{nombre}="):
                return ln.split("=", 1)[1].strip().strip('"').strip("'")
    return str(default)


# ────────────────────────────────────────────────────────────────────
# QUERIES
# ────────────────────────────────────────────────────────────────────

def stock_por_clave(db) -> dict:
    """Devuelve {(colegio, id_producto, talla): stock_actual}."""
    rows = db.session.execute(text("""
        SELECT s.id_colegio, c.nombre  AS colegio,
               s.id_producto, p.nombre AS producto, p.tipo,
               s.talla_individual, COALESCE(s.cantidad, 0) AS stock
        FROM stock s
        JOIN colegios c ON c.id_colegio = s.id_colegio
        JOIN productos p ON p.id_producto = s.id_producto
    """)).mappings().all()
    out = {}
    for r in rows:
        k = (r["colegio"], r["id_producto"], r["producto"], r["tipo"], r["talla_individual"])
        # si hay duplicados (no debería), sumamos
        out[k] = out.get(k, 0) + int(r["stock"] or 0)
    return out


def velocidad_90d(db, hace_dias: int) -> dict:
    """Devuelve {(colegio, id_producto, talla): unidades_vendidas} en los últimos
    `hace_dias` desde la tabla factura_detalle (POS). No es la web porque tiene
    muy poco volumen histórico."""
    desde = date.today() - timedelta(days=hace_dias)
    rows = db.session.execute(text("""
        SELECT c.nombre AS colegio, fd.id_producto,
               fd.talla_individual, SUM(fd.cantidad) AS u
        FROM facturas f
        JOIN colegios c        ON c.id_colegio = f.id_colegio
        JOIN factura_detalle fd ON fd.id_factura = f.id_factura
        WHERE f.estado != 'ANULADA'
          AND f.fecha_factura >= :desde
        GROUP BY c.nombre, fd.id_producto, fd.talla_individual
    """), {"desde": desde}).mappings().all()
    out = {}
    for r in rows:
        k = (r["colegio"], r["id_producto"], r["talla_individual"])
        out[k] = int(r["u"] or 0)
    return out


# ────────────────────────────────────────────────────────────────────
# CATEGORIZACIÓN
# ────────────────────────────────────────────────────────────────────

def clasificar(stock: int, vendidas: int, ventana_dias: int, umbral: int) -> tuple[str, float | None]:
    """
    Retorna (categoria, semanas_restantes).
      CRITICA / ALTA / MEDIA / BAJA / None
    Donde None de (cat, sem) significa "no alertar".
    """
    if stock <= 0:
        # Agotado: crítico solo si tiene velocidad > 0 (si nunca se vende → no alerta aquí)
        if vendidas > 0:
            return "CRITICA", 0.0
        return "BAJA", None

    if stock > umbral:
        return "NINGUNA", None

    if vendidas > 0:
        u_dia = vendidas / ventana_dias
        sem_rest = stock / max(u_dia * 7, 0.01)
        if sem_rest < 4:
            return "CRITICA", round(sem_rest, 1)
        if sem_rest < 8:
            return "ALTA",   round(sem_rest, 1)
        return "MEDIA",    round(sem_rest, 1)

    # <= umbral y sin venta reciente -> MEDIA (vigilar pero no gritar)
    return "MEDIA", None


# ────────────────────────────────────────────────────────────────────
# ESTADO INCREMENTAL
# ────────────────────────────────────────────────────────────────────

def cargar_estado() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_estado(alertas: list) -> None:
    keys = sorted({a["key"] for a in alertas})
    STATE_FILE.write_text(json.dumps({"fecha": datetime.now().isoformat(timespec="seconds"),
                                       "keys": keys}, indent=2, ensure_ascii=False),
                          encoding="utf-8")


def diff_nuevas(alertas, prev_state) -> list:
    prev = set(prev_state.get("keys", []))
    return [a for a in alertas if a["key"] not in prev]


# ────────────────────────────────────────────────────────────────────
# PRINT & MAIN
# ────────────────────────────────────────────────────────────────────

def seccion(t) -> None:
    print()
    print("═" * 78)
    print(f"  {t}")
    print("═" * 78)


def tabla_md(headers, filas) -> None:
    if not filas:
        print("| " + " | ".join(headers) + " |")
        print("|" + "|".join("---" for _ in headers) + "|")
        print("| (vacío) |" * len(headers))
        return
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for f in filas:
        print("| " + " | ".join(str(c) if c is not None else "-" for c in f) + " |")


def construir_mensaje(alertas: list, nuevas: list, umbral: int, ventana: int) -> tuple[str, str]:
    criticas = [a for a in alertas if a["cat"] == "CRITICA"]
    altas    = [a for a in alertas if a["cat"] == "ALTA"]
    nuevas_crit  = [a for a in nuevas if a["cat"] == "CRITICA"]

    if not criticas and not altas:
        asunto = f"RALOZ stock: todo bien ({len(alertas)} alertas MEDIA/Baja)"
    elif nuevas_crit:
        asunto = f"🚨 RALOZ: {len(nuevas_crit)} stock CRÍTICAS nuevas · REVISAR YA"
    elif criticas:
        asunto = f"⚠️ RALOZ: {len(criticas)} items con stock crítico (umbral {umbral})"
    else:
        asunto = f"RALOZ stock: {len(altas)} altas · {len(criticas)} críticas"

    lineas = [
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Umbral: stock <= {umbral}  ·  Ventana velocidad: {ventana} días",
        "",
        f"── CRÍTICAS ({len(criticas)}) ──────────── agotado o < 4 semanas de stock",
    ]
    for a in criticas:
        sem = a["sem_rest"]
        sem_txt = f" — ~{sem} semanas restantes" if sem is not None and sem > 0 else ""
        lineas.append(f"  · {a['colegio']} · {a['producto']} T{a['talla']} · stock={a['stock']} · 90d={a['vendidas_90d']}{sem_txt}")
    lineas.append("")
    lineas.append(f"── ALTAS ({len(altas)}) ───────────────────── entre 4 y 8 semanas")
    for a in altas:
        lineas.append(f"  · {a['colegio']} · {a['producto']} T{a['talla']} · stock={a['stock']} · ~{a['sem_rest']} semanas")
    medias = [a for a in alertas if a["cat"] == "MEDIA"]
    if medias:
        lineas.append("")
        lineas.append(f"── MEDIAS ({len(medias)}) ─────────────────── ≤ umbral sin rotación rápida")
        for a in medias[:10]:
            lineas.append(f"  · {a['colegio']} · {a['producto']} T{a['talla']} · stock={a['stock']}")
        if len(medias) > 10:
            lineas.append(f"  · … y {len(medias)-10} más (revisa el CSV completo)")

    if nuevas_crit:
        lineas.append("")
        lineas.append(f"── NUEVAS ESTA CORRIDA ({len(nuevas_crit)}) ─────────────────────")
        for a in nuevas_crit:
            lineas.append(f"  · {a['colegio']} · {a['producto']} T{a['talla']} · stock={a['stock']}")

    return asunto, "\n".join(lineas)


def main(argv: list | None = None):
    if argv is None:
        # tomar sys.argv[1:] cuando se ejecuta como script
        import sys
        argv = sys.argv[1:]
    args = _parsear_args(argv)
    umbral  = args.umbral  or int(leer_env("MAINT_STOCK_UMBRAL", "5"))
    ventana = args.ventana or int(leer_env("MAINT_STOCK_VENTANA", "90"))
    csv_dir = Path(args.csv_dir) if args.csv_dir else None
    print(f"# Alertas de stock RALOZ COL S.A.S · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Umbral: stock <= {umbral}  ·  Ventana velocidad: {ventana} días")

    app = create_app()
    with app.app_context():
        db = app.extensions['migrate'].db if 'migrate' in app.extensions else __import__('app.db', fromlist=['db']).db
        stock   = stock_por_clave(db)
        vendido = velocidad_90d(db, ventana)

        # Unir
        alertas = []
        for (colegio, ip, prod, tipo, ti), stk in stock.items():
            vendidas = vendido.get((colegio, ip, ti), 0)
            cat, sem = clasificar(stk, vendidas, ventana, umbral)
            if cat == "NINGUNA":
                continue
            key = f"{colegio}|{ip}|{ti}"
            alertas.append({
                "key":         key,
                "colegio":     colegio,
                "id_producto": ip,
                "producto":    prod,
                "tipo":        tipo or "",
                "talla":       ti,
                "stock":       stk,
                "vendidas_90d":vendidas,
                "sem_rest":    sem,
                "cat":         cat,
            })

        # Orden: críticas primero, después altas, después medias
        orden = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2}
        # Filtramos BAJA del reporte stdout (se van igual al CSV para auditoría)
        alertas_reporte = [a for a in alertas if a["cat"] != "BAJA"]
        alertas.sort(key=lambda a: (orden.get(a["cat"], 99), -a["vendidas_90d"], a["colegio"], a["producto"], a["talla"]))

        # Estado
        prev = cargar_estado()
        nuevas = diff_nuevas(alertas, prev)

        seccion(f"ALERTAS ACTIVAS ({len(alertas_reporte)} críticas+altas+medias · {len(nuevas)} nuevas vs corrida anterior)")
        tabla_md(
            ["Cat", "Colegio", "Producto", "Talla", "Stock", "Vendido 90d", "Sem. restantes"],
            [[a["cat"], a["colegio"], a["producto"], a["talla"], a["stock"], a["vendidas_90d"], a["sem_rest"] if a["sem_rest"] is not None else "-"]
             for a in alertas_reporte],
        )

        seccion("RESUMEN POR COLEGIO")
        cols = {}
        for a in alertas:
            cols.setdefault(a["colegio"], {"CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAJA": 0})
            cols[a["colegio"]][a["cat"]] += 1
        tabla_md(
            ["Colegio", "Críticas", "Altas", "Medias", "Bajas"],
            [[c, v["CRITICA"], v["ALTA"], v["MEDIA"], v["BAJA"]] for c, v in sorted(cols.items())],
        )

        if nuevas:
            seccion(f"NUEVAS ESTA CORRIDA ({len(nuevas)})")
            tabla_md(
                ["Cat", "Colegio", "Producto", "Talla", "Stock", "Vendido 90d"],
                [[a["cat"], a["colegio"], a["producto"], a["talla"], a["stock"], a["vendidas_90d"]]
                 for a in nuevas],
            )

        # CSV
        if csv_dir:
            csv_dir.mkdir(parents=True, exist_ok=True)
            path = csv_dir / f"alertas_stock_{date.today().isoformat()}.csv"
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["categoria", "colegio", "id_producto", "producto", "tipo",
                            "talla", "stock", "vendidas_90d", "semanas_restantes",
                            "nueva"])
                for a in alertas:
                    w.writerow([a["cat"], a["colegio"], a["id_producto"], a["producto"],
                                a["tipo"], a["talla"], a["stock"], a["vendidas_90d"],
                                a["sem_rest"] if a["sem_rest"] is not None else "",
                                a["key"] in {n["key"] for n in nuevas}])
            print(f"\nCSV: {path}")

        # Estado y notificación
        guardar_estado(alertas)
        criticas = [a for a in alertas if a["cat"] == "CRITICA"]
        nuevas_crit = [a for a in nuevas if a["cat"] == "CRITICA"]

        # Solo avisar si hay CRÍTICAS (nuevas o recurrentes) o ALTAS nuevas.
        # No notificar si solo hay MEDIAS — ese ya es "vigilar pero no actuar".
        debe_avisar = bool(nuevas_crit) or bool(criticas and any(a for a in alertas if a["cat"] in ("CRITICA", "ALTA") and a["key"] in {n["key"] for n in nuevas}))

        if not debe_avisar:
            print("\nSin alertas críticas nuevas — no se envía email.")
        elif args.no_notify:
            print("\n--no-notify activo. No envío email.")
        else:
            asunto, cuerpo = construir_mensaje(alertas, nuevas, umbral, ventana)
            res = enviar_email(asunto, cuerpo)
            print(f"\nNotificación: {res}")
        print("\n# Fin.")


if __name__ == "__main__":
    BACKEND = Path(__file__).resolve().parents[1]
    main()
