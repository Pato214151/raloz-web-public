"""
RALOZ COL S.A.S — Reporte semanal de operaciones (#8).

Lee la BD (solo SELECT) y resume la semana anterior en un email/csv:

  1. Ventas de los últimos 7 días (POS + web)
  2. Facturas pendientes de entrega (POR_ENTREGAR, LISTO_LLAMAR, EMPACADO)
  3. Saldos pendientes de pago (dinero que aún no se cobra)
  4. Abonos cobrados en la semana
  5. Top 5 colegios por venta semanal
  6. Cruzado con .last_state.json y .stock_alerts_state.json

Disparado por: GitHub Actions manual o semanalmente (configurable en workflow).

USO:
    cd backend
    python tools/reporte_semanal.py                                # semana anterior
    python tools/reporte_semanal.py --desde 2025-08-04 --hasta 2025-08-10
    python tools/reporte_semanal.py --csv-dir backups/
    python tools/reporte_semanal.py --no-notify                     # no envía email
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

BACKEND = Path(__file__).resolve().parents[1]
STATE_MAIN   = BACKEND / "backups" / ".last_state.json"
STATE_STOCK  = BACKEND / "backups" / ".stock_alerts_state.json"


def parsear_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default=None, help="YYYY-MM-DD (default: hace 7 días)")
    ap.add_argument("--hasta", default=None, help="YYYY-MM-DD (default: hoy)")
    ap.add_argument("--csv-dir", default=None,
                    help="Carpeta donde escribir el CSV del reporte")
    ap.add_argument("--no-notify", action="store_true",
                    help="No enviar email (imprime el cuerpo)")
    ap.add_argument("--email-para", default=None,
                    help="Override del destino (usar tools.notifier.leer_env por defecto)")
    return ap.parse_args()


# ────────────────────────────────────────────────────────────────────
# QUERIES (cada una retorna filas; main las une)
# ────────────────────────────────────────────────────────────────────

def ventas_pos_periodo(db, d, h):
    """Ventas POS por colegio y por día."""
    return db.session.execute(text("""
        SELECT f.fecha_factura::date AS dia,
               c.nombre AS colegio,
               COUNT(DISTINCT f.id_factura) AS facturas,
               SUM(fd.cantidad) AS unidades,
               SUM(f.total) AS ingresos
        FROM facturas f
        JOIN colegios c ON c.id_colegio = f.id_colegio
        JOIN factura_detalle fd ON fd.id_factura = f.id_factura
        WHERE f.estado != 'ANULADA'
          AND f.fecha_factura >= :d
          AND f.fecha_factura <  :h
        GROUP BY c.nombre, f.fecha_factura
        ORDER BY f.fecha_factura DESC, ingresos DESC
    """), {"d": d, "h": h}).mappings().all()


def ventas_web_periodo(db, d, h):
    """Pedidos web pagados en el período."""
    return db.session.execute(text("""
        SELECT DATE(fecha_pago) AS dia,
               COALESCE(nombre_colegio, 's/c') AS colegio,
               COUNT(*) AS pedidos,
               SUM(total) AS ingresos
        FROM pedidos_web
        WHERE estado = 'pagado'
          AND fecha_pago >= :d
          AND fecha_pago <  :h
        GROUP BY DATE(fecha_pago), nombre_colegio
        ORDER BY dia DESC, ingresos DESC
    """), {"d": d, "h": h}).mappings().all()


def pendientes_entrega(db):
    """Facturas pendientes de entregar (POR_ENTREGAR, LISTO_LLAMAR, EMPACADO)."""
    return db.session.execute(text("""
        SELECT estado_entrega, COUNT(*) AS n,
               COALESCE(SUM(total), 0) AS monto,
               MIN(fecha_factura) AS mas_vieja,
               MAX(fecha_factura) AS mas_nueva
        FROM facturas
        WHERE estado != 'ANULADA'
          AND estado_entrega IN ('POR_ENTREGAR','LISTO_LLAMAR','EMPACADO')
        GROUP BY estado_entrega
    """)).mappings().all()


def saldos_pendientes(db):
    """Facturas no anuladas con saldo pendiente > 0."""
    return db.session.execute(text("""
        SELECT f.numero_factura,
               f.id_colegio, c.nombre AS colegio,
               f.cliente_nombre,
               f.total, COALESCE(f.total_abonado, 0) AS abonado,
               COALESCE(f.saldo_pendiente, 0) AS saldo,
               f.fecha_factura, f.estado_entrega
        FROM facturas f
        JOIN colegios c ON c.id_colegio = f.id_colegio
        WHERE f.estado != 'ANULADA'
          AND COALESCE(f.saldo_pendiente, 0) > 0
        ORDER BY saldo DESC
        LIMIT 20
    """)).mappings().all()


def abonos_periodo(db, d, h):
    """Suma de abonos recibidos en el período (no solo POS)."""
    r = db.session.execute(text("""
        SELECT COUNT(*) AS n_pagos,
               COALESCE(SUM(valor), 0) AS total
        FROM pagos
        WHERE fecha_pago >= :d
          AND fecha_pago <  :h
    """), {"d": d, "h": h}).mappings().first()
    return {"n": int(r["n_pagos"] or 0), "total": float(r["total"] or 0)}


# ────────────────────────────────────────────────────────────────────
# PRINT HELPERS
# ────────────────────────────────────────────────────────────────────

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
        print("| " + " | ".join(headers) + " |")
        print("|" + "|".join("---" for _ in headers) + "|")
        print("| (vacío) |" * len(headers))
        return
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for fila in filas:
        print("| " + " | ".join(str(c) if c is not None else "-" for c in fila) + " |")


# ────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────

def cargar_estados():
    out = {"weekly": {}, "stock": {}}
    if STATE_MAIN.exists():
        try:
            out["weekly"] = json.loads(STATE_MAIN.read_text(encoding="utf-8"))
        except Exception:
            pass
    if STATE_STOCK.exists():
        try:
            out["stock"] = json.loads(STATE_STOCK.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def construir_mensaje(resumen, desde, hasta, estados):
    lineas = [
        f"Período: {desde.isoformat()} → {hasta.isoformat()}",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "── VENTAS DE LA SEMANA ─────────────────────",
    ]
    pos = resumen["ventas_pos"]
    web = resumen["ventas_web"]
    lineas.append(f"  POS:   {pos['facturas']} facturas · {pos['unidades']} unidades · {fmt_cop(pos['ingresos'])}")
    lineas.append(f"  Web:   {web['pedidos']} pedidos · {fmt_cop(web['ingresos'])}")
    lineas.append(f"  TOTAL: {fmt_cop(pos['ingresos'] + web['ingresos'])}")
    lineas.append(f"  Abonos cobrados: {resumen['abonos']['n']} pagos · {fmt_cop(resumen['abonos']['total'])}")
    lineas.append("")

    lineas.append("── TOP COLEGIOS DE LA SEMANA (POS) ──────────")
    for r in resumen["top_colegios_pos"]:
        lineas.append(f"  · {r['colegio']}: {fmt_cop(r['ingresos'])} ({r['facturas']} fact.)")
    lineas.append("")

    lineas.append("── PENDIENTES DE ENTREGA ───────────────")
    if resumen["pendientes_entrega"]:
        for r in resumen["pendientes_entrega"]:
            lineas.append(f"  · {r['estado_entrega']}: {r['n']} facturas, {fmt_cop(r['monto'])}")
    else:
        lineas.append("  · Sin pendientes de entrega")
    lineas.append("")

    lineas.append("── SALDOS PENDIENTES (lo que te deben) ───────")
    if resumen["saldos"]:
        total_saldo = sum(s["saldo"] for s in resumen["saldos"])
        lineas.append(f"  · {len(resumen['saldos'])} facturas con saldo · total {fmt_cop(total_saldo)}")
        for r in resumen["saldos"][:5]:
            cli = (r["cliente_nombre"] or "")[:24]
            lineas.append(f"     {r['numero_factura']} · {r['colegio']} · {cli} · {fmt_cop(r['saldo'])}")
        if len(resumen["saldos"]) > 5:
            lineas.append(f"     … y {len(resumen['saldos'])-5} más (ver CSV)")
    else:
        lineas.append("  · Sin saldos pendientes")
    lineas.append("")

    # cruzado con weekly maintenance
    if estados.get("weekly", {}).get("hallazgos"):
        lineas.append("── HALLAZGOS DE INTEGRIDAD (state latest) ───")
        for k, v in estados["weekly"]["hallazgos"].items():
            if k in ("total", "__resumen_total__") or not isinstance(v, int):
                continue
            lineas.append(f"  · {k}: {v}")
        lineas.append("")

    if estados.get("stock"):
        n_stock = len(estados["stock"].get("keys", []))
        lineas.append("── ALERTAS DE STOCK ────────────────────────")
        lineas.append(f"  · {n_stock} alertas activas registradas (revisa el correo de mantenimiento)")
        lineas.append("")

    lineas.append("Detalle en el CSV adjunto (si se generó con --csv-dir backups/).")
    return "\n".join(lineas)


def main():
    args = parsear_args()
    hoy = date.today()
    hasta = date.fromisoformat(args.hasta) if args.hasta else hoy
    desde = date.fromisoformat(args.desde) if args.desde else (hasta - timedelta(days=7))

    print(f"# Reporte semanal RALOZ COL S.A.S · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Período: {desde.isoformat()} → {hasta.isoformat()}")
    csv_dir = Path(args.csv_dir) if args.csv_dir else None

    app = create_app()
    with app.app_context():
        db = app.extensions['migrate'].db if 'migrate' in app.extensions else __import__('app.db', fromlist=['db']).db

        # Ventas POS: agrupadas por colegio
        rows_pos = ventas_pos_periodo(db, desde, hasta)
        # agregar también por colegio
        por_colegio = {}
        total_pos = {"facturas": set(), "unidades": 0, "ingresos": 0.0}
        for r in rows_pos:
            dia = str(r["dia"])
            cn = r["colegio"]
            por_colegio.setdefault(cn, {"facturas": 0, "unidades": 0, "ingresos": 0.0,
                                         "dias": {}})
            por_colegio[cn]["facturas"] += r["facturas"]
            por_colegio[cn]["unidades"] += int(r["unidades"] or 0)
            por_colegio[cn]["ingresos"] += float(r["ingresos"] or 0)
            por_colegio[cn]["dias"][dia] = por_colegio[cn]["dias"].get(dia, 0) + float(r["ingresos"] or 0)
            total_pos["facturas"].add(r["facturas"])  # dummy:不能用
        # recalcular total_pos bien
        total_pos = {
            "facturas": sum(por_colegio[c]["facturas"] for c in por_colegio),
            "unidades": sum(por_colegio[c]["unidades"] for c in por_colegio),
            "ingresos": sum(por_colegio[c]["ingresos"] for c in por_colegio),
        }

        rows_web = ventas_web_periodo(db, desde, hasta)
        web_por_colegio = {}
        total_web = {"pedidos": 0, "ingresos": 0.0}
        for r in rows_web:
            cn = r["colegio"]
            web_por_colegio.setdefault(cn, {"pedidos": 0, "ingresos": 0.0})
            web_por_colegio[cn]["pedidos"] += r["pedidos"]
            web_por_colegio[cn]["ingresos"] += float(r["ingresos"] or 0)
            total_web["pedidos"] += r["pedidos"]
            total_web["ingresos"] += float(r["ingresos"] or 0)

        pendientes = pendientes_entrega(db)
        saldos = saldos_pendientes(db)
        abonos = abonos_periodo(db, desde, hasta)

        top_pos = sorted(
            [{"colegio": c, **v} for c, v in por_colegio.items()],
            key=lambda r: -r["ingresos"],
        )[:5]

    resumen = {
        "ventas_pos": total_pos,
        "ventas_web": total_web,
        "abonos": abonos,
        "top_colegios_pos": top_pos,
        "pendientes_entrega": [dict(r) for r in pendientes],
        "saldos": [dict(r) for r in saldos],
    }

    # ── Print principal ──────────────────────────────────────
    seccion(f"VENTAS POS POR COLEGIO (semana {desde} → {hasta})")
    tabla_md(
        ["Colegio", "Facturas", "Unidades", "Ingresos"],
        [[c,
          por_colegio[c]["facturas"],
          por_colegio[c]["unidades"],
          fmt_cop(por_colegio[c]["ingresos"])]
         for c in por_colegio],
    )

    if web_por_colegio:
        seccion("VENTAS WEB POR COLEGIO")
        tabla_md(
            ["Colegio", "Pedidos", "Ingresos"],
            [[c, web_por_colegio[c]["pedidos"], fmt_cop(web_por_colegio[c]["ingresos"])]
             for c in web_por_colegio],
        )

        seccion("PENDIENTES DE ENTREGA")
        tabla_md(
            ["Estado", "Cantidad", "Monto total", "Más vieja", "Más nueva"],
            [[r["estado_entrega"], r["n"], fmt_cop(r["monto"]),
              str(r["mas_vieja"]), str(r["mas_nueva"])]
             for r in pendientes],
        )

        seccion("SALDOS PENDIENTES (top 20)")
        tabla_md(
            ["Factura", "Colegio", "Cliente", "Total", "Abonado", "Saldo", "Estado"],
            [[r["numero_factura"], r["colegio"],
              (r["cliente_nombre"] or "")[:30],
              fmt_cop(r["total"]),
              fmt_cop(r["abonado"]),
              fmt_cop(r["saldo"]),
              r["estado_entrega"]]
             for r in saldos],
        )

        if not pendientes and not saldos:
            print("\n[OK] Sin pendientes de entrega ni saldos pendientes.")

        # CSV del resumen completo (para análisis en Excel)
        if csv_dir:
            csv_dir.mkdir(parents=True, exist_ok=True)
            # 1 CSV detallado de facturas (todo el dataset, no solo top)
            rows_full = db.session.execute(text("""
                SELECT f.numero_factura, f.id_colegio, f.fecha_factura,
                       f.cliente_nombre, f.total, f.total_abonado,
                       f.saldo_pendiente, f.estado_entrega, f.fecha_entrega
                FROM facturas f
                WHERE f.estado != 'ANULADA'
                  AND (f.estado_entrega IN ('POR_ENTREGAR','LISTO_LLAMAR','EMPACADO')
                       OR COALESCE(f.saldo_pendiente, 0) > 0)
                  AND f.fecha_factura >= :d
                ORDER BY f.fecha_factura DESC
            """), {"d": desde - timedelta(days=30)}).mappings().all()
            full_path = csv_dir / f"reporte_facturas_{desde}_{hasta}.csv"
            with open(full_path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["numero_factura", "id_colegio", "fecha_factura",
                           "cliente_nombre", "total", "total_abonado",
                           "saldo_pendiente", "estado_entrega", "fecha_entrega"])
                w.writerows([r["numero_factura"], r["id_colegio"],
                             str(r["fecha_factura"]),
                             r["cliente_nombre"] or "",
                             r["total"] or 0, r["total_abonado"] or 0,
                             r["saldo_pendiente"] or 0,
                             r["estado_entrega"] or "",
                             str(r["fecha_entrega"] or "")]
                            for r in rows_full)
            print(f"\nCSV: {full_path} ({len(rows_full)} filas)")

        # Email
        estados = cargar_estados()
        cuerpo = construir_mensaje(resumen, desde, hasta, estados)
        asunto = (f"RALOZ semana {desde} → {hasta}: "
                  f"{fmt_cop(total_pos['ingresos'] + total_web['ingresos'])} · "
                  f"{len(saldos)} saldos · {sum(p['n'] for p in pendientes)} pendientes")
        if args.no_notify:
            print("\n--no-notify activo. Cuerpo del email:\n" + cuerpo)
        else:
            res = enviar_email(asunto, cuerpo)
            print(f"\nNotificación: {res}")
        print("\n# Fin.")


if __name__ == "__main__":
    main()
