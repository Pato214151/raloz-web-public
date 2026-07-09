"""
RALOZ COL S.A.S — Mantenimiento semanal automatizado.

Orquesta el backup de la BD y el diagnóstico de integridad, sin romper lo que
ya hacen backup_db.py / diagnostico_datos.py (se reusan como módulos).

Salidas:
  - SQL dump en    backend/backups/raloz_backup_YYYY-MM-DD_HHMM.sql
  - Log + JSON con resumen en backend/backups/.last_state.json
  - Retención: conserva los últimos 8 semanales + 12 anclas mensuales
  - Notificación por email (Brevo) si hay hallazgos NUEVOS vs última ejecución
    — opcional, depende de EMAIL_AVISO_TO + BREVO_API_KEY.

Uso local:
    cd backend
    python tools/maintenance.py                   # backup + diagnóstico + alerta
    python tools/maintenance.py --no-backup      # solo diagnóstico
    python tools/maintenance.py --no-notify      # sin email (solo imprime)
    python tools/maintenance.py --reset-state    # borra el .last_state.json
                 (próximo run avisará de todos los hallazgos como "nuevos")

Pensado para correr semanalmente desde GitHub Actions (lunes 3 am COL).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths de archivo (los módulos sí importan bajo "tools.*", por eso añadimos
# el padre en sys.path al importar el notifier más abajo).
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent  # noqa: F841  (usado por helpers más abajo)
BACKUPS_DIR = BACKEND / "backups"
STATE_FILE = BACKUPS_DIR / ".last_state.json"

# Permite ejecutar el script desde "backend/" o desde cualquier cwd agregando
# el directorio backend al sys.path (necesario para "import tools.notifier").
sys.path.insert(0, str(BACKEND))

# UTF-8 en consola: evita UnicodeEncodeError con emojis/═ en Windows (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")   # type: ignore[attr-defined]
except Exception:
    pass

# Reutilizamos el notifier (también lo usa el reporte semanal en el futuro)
from tools.notifier import enviar_email as _enviar_email_brevo  # type: ignore

# Tablas que DEBEN existir en un backup válido (si falta alguna → alerta CRÍTICA).
# Nombres reales en la BD (verificado contra un dump real): SIEMPRE en plural,
# snake_case, con comillas dobles en los INSERTs.
TABLAS_CRITICAS = (
    "facturas",
    "pagos",
    "pedidos_web",
    "stock",
    "productos",
    "colegios",
    "precios_colegio",
)


# ── Helpers ───────────────────────────────────────────────────────────
def log(msg: str) -> None:
    """Log con timestamp corto, siempre a stderr (no rompe captura de JSON)."""
    sys.stderr.write(f"[maintenance {datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()


def leer_env(nombre: str, default: str = "") -> str:
    """Lee de os.getenv o del .env del backend (sin librerías)."""
    val = os.getenv(nombre, "").strip()
    if val:
        return val
    env_file = BACKEND / ".env"
    if env_file.exists():
        for linea in env_file.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith(f"{nombre}="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return default


# ── Backup ────────────────────────────────────────────────────────────
def ejecutar_backup() -> dict:
    """Corre backup_db.py como subproceso y devuelve un resumen estructurado."""
    log("Ejecutando backup_db.py …")
    proc = subprocess.run(
        [sys.executable, str(HERE / "backup_db.py")],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    ok = proc.returncode == 0

    # Parsear: el archivo queda en backend/backups/raloz_backup_FECHA.sql
    sql_files = sorted(BACKUPS_DIR.glob("raloz_backup_*.sql"))
    last_sql  = sql_files[-1] if sql_files else None

    resumen = {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-800:],
        "archivo":    str(last_sql) if last_sql else None,
        "tam_kb":     round(last_sql.stat().st_size / 1024, 1) if last_sql else 0,
    }
    log(f"Backup: {'OK' if ok else 'FALLO'} ({resumen['tam_kb']} KB)")
    return resumen


# ── Diagnóstico ────────────────────────────────────────────────────────
def ejecutar_diagnostico() -> dict:
    """
    Corre diagnostico_datos.py y parsea su salida. Como ese script imprime a
    stdout sin devolver un código de error diferenciado, contamos los
    "Total:" / "Total descuadradas:" / "Total con referencias rotas:" etc.
    Capturamos stdout a un buffer para no contaminar la salida del cron.
    """
    log("Ejecutando diagnostico_datos.py …")
    buf_out, buf_err = io.StringIO(), io.StringIO()
    proc = subprocess.run(
        [sys.executable, str(HERE / "diagnostico_datos.py")],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    # Aunque el script no falle (returncode 0), reportamos los conteos.
    hallazgos = _parsear_conteos_hallazgos(out)
    log(f"Diagnóstico: {hallazgos.get('total', 0)} hallazgos")
    return {
        "ok": True,
        "returncode": proc.returncode,
        "stdout": out,
        "hallazgos": hallazgos,
    }


# Regex súper tolerantes: en cada sección imprime "Total: N" o "Total X: N"
_SECCION_RE = re.compile(
    r"(?im)^\s*(?:Total|TOTAL)\s*(?:[a-zA-Záéíóúñ 0-9_]*?)[:=]\s*(\d+)"
)
_RESUMEN_RE = re.compile(r"(?im)RESUMEN:\s*(\d+)\s+hallazgos")
_HUERFANO_RE = re.compile(r"(?i)huérfan[ao]s?:\s*(\d+)")
_DES_CUADRADAS_RE = re.compile(r"(?i)descuadradas?:\s*(\d+)")


def _parsear_conteos_hallazgos(stdout: str) -> dict:
    """
    Devuelve un dict con conteo por categoría y total agregado.
    Usa dos estrategias: (a) parseo por secciones, (b) búsqueda de patrones
    conocidos. Si los nombres cambian, devolvemos al menos el resumen final.
    """
    resumen: dict[str, int] = {}

    # 1. Sección por sección (mejor esfuerzo)
    lineas = stdout.splitlines()
    seccion_actual = ""
    for ln in lineas:
        m = re.match(r"\s*([0-9]\w?[\.\)]?)\s*\.?([A-Za-z].+?)\s*$", ln)
        if m:
            seccion_actual = m.group(2).strip().rstrip(":")
        m2 = re.match(r"^\s*(?:Total|total)[:\s]+(\d+)", ln)
        if m2 and seccion_actual:
            # solo nos quedamos con las que parecen conteos de problemas
            resumen[seccion_actual] = int(m2.group(1))

    # 2. Patrones explícitos (siempre intentamos)
    m = _RESUMEN_RE.search(stdout)
    if m:
        resumen["__resumen_total__"] = int(m.group(1))

    for label, pat in (
        ("huerfanos", _HUERFANO_RE),
        ("descuadradas", _DES_CUADRADAS_RE),
    ):
        m = pat.search(stdout)
        if m:
            resumen[label] = int(m.group(1))

    # 3. Total agregado (usamos el resumen si existe; si no, sumamos las secciones)
    if "__resumen_total__" in resumen:
        total = resumen["__resumen_total__"]
    else:
        total = sum(v for k, v in resumen.items() if k != "__resumen_total__")
    resumen["total"] = total
    return resumen


# ── Verificación del backup ────────────────────────────────────────────
def verificar_backup(archivo: str | None) -> dict:
    """
    Comprueba que el SQL dump no esté vacío/truncado y que contenga
    las tablas críticas. Devuelve {"ok": bool, "problemas": [str, ...]}.
    """
    problemas: list[str] = []
    if not archivo or not Path(archivo).exists():
        return {"ok": False, "problemas": ["No se generó el archivo de backup."]}
    p = Path(archivo)
    if p.stat().st_size < 1024:
        problemas.append(f"Archivo demasiado pequeño: {p.stat().st_size} bytes.")
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "BEGIN;" not in txt or "COMMIT;" not in txt:
        problemas.append("No contiene BEGIN/COMMIT (dump incompleto).")
    # Sentencias CREATE? No las esperamos (backup es solo INSERTs). Verificar
    # que al menos hay sentencias INSERT INTO <critica>.
    for tabla in TABLAS_CRITICAS:
        if not re.search(rf'INSERT\s+INTO\s+"{tabla}"', txt, re.IGNORECASE):
            problemas.append(f"Falta INSERT INTO {tabla}.")
    return {"ok": not problemas, "problemas": problemas}


# ── Retención ──────────────────────────────────────────────────────────
def aplicar_retencion(keep_weekly: int = 8, keep_monthly: int = 12) -> dict:
    """
    Conserva `keep_weekly` archivos semanales (los más recientes) y
    `keep_monthly` archivos anclados al día 1 de cada mes (los más recientes).
    Borra el resto. Devuelve cuántos se borraron.
    """
    if not BACKUPS_DIR.exists():
        return {"borrados": 0}
    files = sorted(
        BACKUPS_DIR.glob("raloz_backup_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # semanales: los keep_weekly más recientes
    keep = set(files[:keep_weekly])
    # mensuales: el primero de cada mes (que aparezca entre los archivos)
    seen_months: set[str] = set()
    for f in files:
        m = re.search(r"raloz_backup_(\d{4}-\d{2})-(\d{2})_", f.name)
        if m and m.group(2) == "01":  # día 01 = ancla mensual
            seen_months.add(m.group(1))
            keep.add(f)
        if len([k for k in keep if k == f]) == 0 and len(seen_months) >= keep_monthly:
            break
    # limitar anclas mensuales
    months_sorted = sorted(seen_months, reverse=True)
    meses_a_borrar = set(months_sorted[keep_monthly:])
    if meses_a_borrar:
        for f in list(keep):
            m = re.search(r"raloz_backup_(\d{4}-\d{2})-", f.name)
            if m and m.group(1) in meses_a_borrar:
                keep.discard(f)

    borrados = 0
    for f in files:
        if f not in keep:
            try:
                f.unlink()
                borrados += 1
            except OSError:
                pass
    log(f"Retención: {borrados} backups antiguos borrados, {len(keep)} conservados.")
    return {"borrados": borrados, "conservados": len(keep)}


# ── Estado incremental ────────────────────────────────────────────────
def cargar_estado() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def guardar_estado(estado: dict) -> None:
    BACKUPS_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(estado, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    try:
        STATE_FILE.chmod(0o600)  # por si el sistema lo permite
    except OSError:
        pass


def diff_hallazgos(prev: dict | None, new: dict) -> dict[str, int]:
    """
    Devuelve cuántas categorías tienen conteo MAYOR al de la corrida anterior.
    """
    if not prev or "hallazgos" not in prev:
        return {k: v for k, v in new.items() if isinstance(v, int)}
    prev_h = prev["hallazgos"]
    out: dict[str, int] = {}
    for k, v in new.items():
        if not isinstance(v, int):
            continue
        if v > prev_h.get(k, 0):
            out[k] = v - prev_h.get(k, 0)
    return out


# ── Notificación ───────────────────────────────────────────────────────
def notificar(asunto: str, cuerpo: str) -> dict:
    """Wrapper sobre tools.notifier.enviar_email, mantiene log aquí."""
    res = _enviar_email_brevo(asunto, cuerpo)
    if not res.get("enviado"):
        log(f"Notificación omitida / fallida: {res}")
    return res


def construir_mensaje(diag: dict, backup: dict, verificacion: dict,
                       nuevos_hallazgos: dict[str, int], prev: dict | None) -> tuple[str, str]:
    """Asunto y cuerpo del email si hay hallazgos nuevos o backup crítico."""
    total_prev = (prev or {}).get("hallazgos", {}).get("total")
    total_new  = diag["hallazgos"].get("total")
    criticos   = verificacion["problemas"]

    # asunto
    if criticos:
        asunto = "🚨 RALOZ: backup de BD NO válido (revisar ya)"
    elif nuevos_hallazgos:
        asunto = f"⚠️ RALOZ: {len(nuevos_hallazgos)} categorías empeoraron ({total_new} hallazgos)"
    elif total_prev is not None and total_new is not None and total_new < total_prev:
        asunto = f"✅ RALOZ: mejoró la integridad ({total_prev}→{total_new} hallazgos)"
    else:
        asunto = f"RALOZ mantenimiento semanal OK ({total_new} hallazgos)"

    # cuerpo
    lineas = []
    lineas.append(f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lineas.append("")
    lineas.append("── BACKUP ─────────────────────────────")
    if backup.get("archivo"):
        lineas.append(f"Archivo: {backup['archivo']}")
        lineas.append(f"Tamaño: {backup['tam_kb']} KB")
    lineas.append(f"Verificación: {'OK' if verificacion['ok'] else 'FALLO'}")
    if criticos:
        for c in criticos:
            lineas.append(f"  - {c}")
    lineas.append("")
    lineas.append("── DIAGNÓSTICO ──────────────────────")
    lineas.append(f"Total hallazgos: {total_new}")
    if total_prev is not None:
        lineas.append(f"  (corrida anterior: {total_prev})")
    for k, v in diag["hallazgos"].items():
        if k in ("total", "__resumen_total__"):
            continue
        if not isinstance(v, int):
            continue
        prev_v = (prev or {}).get("hallazgos", {}).get(k)
        marca = ""
        if prev_v is not None:
            if v > prev_v:
                marca = f"  ⬆ (antes {prev_v})"
            elif v < prev_v:
                marca = f"  ⬇ (antes {prev_v})"
        lineas.append(f"  {k}: {v}{marca}")
    if nuevos_hallazgos:
        lineas.append("")
        lineas.append("Categorías que EMPEORARON (investigar):")
        for k, d in nuevos_hallazgos.items():
            lineas.append(f"  +{d} en {k}")
    lineas.append("")
    lineas.append("Acceso al panel: https://raloz-web.onrender.com")
    return asunto, "\n".join(lineas)


# ── Main ──────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-backup", action="store_true", help="Saltar backup (solo diagnóstico)")
    ap.add_argument("--no-notify", action="store_true", help="No enviar email (imprime el cuerpo)")
    ap.add_argument("--reset-state", action="store_true", help="Borra .last_state.json antes de correr")
    args = ap.parse_args()

    BACKUPS_DIR.mkdir(exist_ok=True)
    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()

    log("=== Mantenimiento semanal RALOZ ===")
    prev = cargar_estado()

    backup_res = {"ok": False, "archivo": None, "tam_kb": 0}
    if not args.no_backup:
        backup_res = ejecutar_backup()
    verificacion = verificar_backup(backup_res.get("archivo"))

    diag = ejecutar_diagnostico()
    nuevos = diff_hallazgos(prev, diag["hallazgos"])

    # retención solo si el backup fue OK
    if backup_res.get("ok") and verificacion["ok"]:
        aplicar_retencion()
    else:
        log("No se aplica retención: el backup no pasó la verificación.")

    estado = {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backup": {
            "ok": backup_res.get("ok"),
            "tam_kb": backup_res.get("tam_kb"),
            "archivo": backup_res.get("archivo"),
            "verificacion_ok": verificacion["ok"],
            "verificacion_problemas": verificacion["problemas"],
        },
        "hallazgos": diag["hallazgos"],
        "nuevos_hallazgos": nuevos,
    }
    guardar_estado(estado)
    log(f"Estado guardado en {STATE_FILE}")

    asunto, cuerpo = construir_mensaje(diag, backup_res, verificacion, nuevos, prev)

    # Decidir si avisar:
    # - SIEMPRE si el backup no pasó la verificación (crítico).
    # - SIEMPRE si hubo hallazgos nuevos vs corrida anterior.
    # - SIEMPRE si mejoró vs corrida anterior (buenas noticias también).
    # - NUNCA si es la primera corrida Y todo está OK y no hubo cambios
    #   (no queremos spamear con "OK sin cambios" la 1ra vez).
    total_prev = (prev or {}).get("hallazgos", {}).get("total")
    total_new  = diag["hallazgos"].get("total")

    backup_critico = not verificacion["ok"]
    hay_nuevos     = bool(nuevos)
    mejoro         = (total_prev is not None
                     and total_new is not None
                     and total_new < total_prev)
    primera_corrida_sin_cambios = (
        prev is None
        and not backup_critico
        and total_new is not None
    )

    debe_avisar = backup_critico or hay_nuevos or mejoro or not primera_corrida_sin_cambios

    if not debe_avisar:
        log("Primera corrida sin cambios — sin email.")
    elif args.no_notify:
        log("--no-notify activo. Cuerpo del email:\n" + cuerpo)
    else:
        res = notificar(asunto, cuerpo)
        log(f"Notificación: {res}")

    # Paso extra: alertas de stock (#7) — independiente del backup.
    # No las mezclamos con el aviso del mantenimiento: cada script decide
    # si avisar según su propio estado. Si llega a fallar, no abortamos.
    try:
        from tools.alertas_stock import main as _run_alertas
        log("Lanzando alertas_stock (autosuficiente)...")
        _run_alertas([])   # [] para que no lea sys.argv (le pasamos sin args)
    except Exception as e:
        log(f"alertas_stock falló: {e}")

    log("=== Mantenimiento finalizado ===")
    return 0 if backup_res.get("ok") and verificacion["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
