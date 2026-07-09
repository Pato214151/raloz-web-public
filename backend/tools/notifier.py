"""
RALOZ COL S.A.S — Notificador genérico por email (Brevo).

Pensado para ser usado por el mantenimiento semanal y por el reporte semanal
(#8, futuro). Solo envía emails transaccionales simples (sin adjuntos), al
mismo destino configurado en EMAIL_AVISO_TO.

NO envía a clientes — para eso está app/utils/email_service.py que arma
facturas PDF y va por el cliente.

Variables leídas (de os.environ o del .env del backend):
  BREVO_API_KEY      obligatorio para enviar
  EMAIL_AVISO_TO     destino del aviso interno (ej. dueño / equipo)
  EMAIL_REMITENTE    remitente (debe estar validado en Brevo)
  EMAIL_NOMBRE       nombre a mostrar del remitente (defecto: "RALOZ COL S.A.S")

Si falta cualquiera, la función devuelve {"enviado": False, "skipped": True}.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


# permite importar este módulo sin tener que ejecutar desde backend/
_BACKEND = Path(__file__).resolve().parents[1]


def leer_env(nombre: str, default: str = "") -> str:
    """Lee variable de entorno o, si no está, del .env del backend."""
    val = os.getenv(nombre, "").strip()
    if val:
        return val
    env_file = _BACKEND / ".env"
    if env_file.exists():
        for linea in env_file.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith(f"{nombre}="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return default


def enviar_email(asunto: str, cuerpo_texto: str) -> dict:
    """
    Envía un email simple por la API v3 de Brevo.

    Retorna:
      {"enviado": True, "status": int}                        — éxito
      {"enviado": False, "skipped": "...", "..."}            — falta config
      {"enviado": False, "status": int, "body": str}         — error Brevo
    """
    api_key = leer_env("BREVO_API_KEY")
    destino = leer_env("EMAIL_AVISO_TO") or leer_env("MAINTENANCE_TO_EMAIL")
    remite  = leer_env("EMAIL_REMITENTE")
    nombre  = leer_env("EMAIL_NOMBRE") or "RALOZ COL S.A.S"

    if not (api_key and destino and remite):
        return {"enviado": False, "skipped": True,
                "razon": "Falta BREVO_API_KEY / EMAIL_AVISO_TO / EMAIL_REMITENTE."}

    if requests is None:
        return {"enviado": False, "skipped": True,
                "razon": "Falta la dependencia 'requests'."}

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "sender":      {"name": nombre, "email": remite},
                "to":          [{"email": destino}],
                "subject":     asunto,
                "textContent": cuerpo_texto,
            },
            timeout=20,
        )
        if 200 <= resp.status_code < 300:
            return {"enviado": True, "status": resp.status_code}
        return {"enviado": False, "status": resp.status_code, "body": resp.text[:500]}
    except Exception as exc:  # pragma: no cover
        return {"enviado": False, "error": str(exc)}


def probar_envio() -> dict:
    """Helper rápido para verificar la config sin mandar nada útil."""
    return {
        "api_key_set":  bool(leer_env("BREVO_API_KEY")),
        "destino":       leer_env("EMAIL_AVISO_TO") or leer_env("MAINTENANCE_TO_EMAIL"),
        "remitente":     leer_env("EMAIL_REMITENTE"),
        "nombre":        leer_env("EMAIL_NOMBRE") or "RALOZ COL S.A.S",
    }
