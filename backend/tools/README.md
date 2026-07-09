# `tools/` — Mantenimiento semanal de RALOZ COL S.A.S

Scripts para asegurar la base de datos y detectar problemas de integridad.

## Scripts incluidos

| Archivo | Qué hace |
|---|---|
| `backup_db.py` | Backup lógico (INSERTs) de todas las tablas → `backend/backups/raloz_backup_FECHA.sql`. **Sigue funcionando tal cual.** |
| `diagnostico_datos.py` | Reporte (no modifica) sobre 7 áreas: huérfanos, pagos descuadrados, kardex, combos más caros, etc. **Sigue funcionando tal cual.** |
| `maintenance.py` | **Nuevo.** Orquestador que corre los dos anteriores, verifica el backup, aplica retención (8 semanales + 12 mensuales), y notifica si hay hallazgos nuevos vs la corrida anterior. |
| `notifier.py` | **Nuevo.** Wrapper genérico para envío de email por Brevo (reutilizado por el reporte semanal cuando llegue). |

## Variables de entorno nuevas

Agregar al `.env.example` (ya están incluidas en este commit):

```
EMAIL_AVISO_TO=correo@ejemplo.com
```

Opcionales (la tarea sigue funcionando sin ellos, solo no se envía email):

```
BREVO_API_KEY=xkeysib-...
EMAIL_REMITENTE=tu_correo@dominio.com   # ya debe existir para facturas
EMAIL_NOMBRE=RALOZ COL SAS               # ya debe existir para facturas
```

> ℹ️ Si **alguna** de las variables opcionales falta, `maintenance.py`
> sigue funcionando: hace backup, diagnóstico, retención y **omite el email**,
> imprimiendo el motivo por stderr. Está a prueba de balas.

---

## Uso local (sin cron)

```
cd backend
python tools/maintenance.py            # todo el flujo
python tools/maintenance.py --no-backup       # solo diagnóstico
python tools/maintenance.py --no-notify       # solo imprimir, sin email
python tools/maintenance.py --reset-state     # próximo run avisará todo como "nuevo"
```

Después de cada corrida, en `backend/backups/`:
- `.last_state.json` — el JSON con totales/hallazgos por categoría y comparación contra la corrida anterior. **Es lo que evita los emails repetitivos.**

---

## Programación semanal (recomendado: GitHub Actions)

Ya hay un workflow en `.github/workflows/weekly-maintenance.yml` que se dispara:

- **Lunes 3:00 am hora Colombia** (`cron: 0 8 * * 1` UTC)
- También manualmente desde la pestaña Actions → "Run workflow"

### Configuración requerida en GitHub (1 sola vez)

1. Ir a `https://github.com/Pato214151/raloz-web/settings/secrets/actions`
2. Crear estos secrets del repo (clic en "New repository secret"):

   | Nombre | Valor | ¿Obligatorio? |
   |---|---|---|
   | `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` (la misma que ya usas) | **Sí** |
   | `BREVO_API_KEY` | tu API key de Brevo (la misma que ya usas para facturas) | No (si no está, solo no se envía email) |
   | `EMAIL_REMITENTE` | remitente validado en Brevo (ya lo tienes para facturas) | No |
   | `EMAIL_AVISO_TO` | a dónde quieres que llegue el aviso interno | No |
   | `EMAIL_NOMBRE` | nombre a mostrar | No |

   Tip: si Brevo ya manda correos a clientes, `BREVO_API_KEY` y `EMAIL_REMITENTE` ya deberían estar ahí. Solo agrega `EMAIL_AVISO_TO`.

3. Después del primer merge a `main`, los lunes aparecerá una ejecución en la pestaña Actions.
4. Cada ejecución sube un artifact `maintenance-<run_id>.zip` con el `.sql` (descargable 90 días) — bájalo y guárdalo aparte (Drive/USB/S3) si quieres.

---

## ¿Qué pasa si sale mal?

| Situación | Qué hace |
|---|---|
| No se puede conectar a la BD | El backup falla → email con "🚨 RALOZ: backup de BD NO válido". Retención se salta (no borramos nada). |
| Hay hallazgos nuevos vs la corrida anterior | Email con "⚠️ empeoraron N categorías". |
| Mejoró la integridad (menos hallazgos) | Email con "✅ mejoró la integridad X→Y". |
| Todo igual, sin cambios | NO se envía email (para no spamearte). El estado se sigue actualizando silenciosamente. |
| El backup no tiene alguna tabla crítica | Backup marcado como NO válido → email crítico + retención se salta. |
| `DATABASE_URL` no está o falla | Acción falla en el step "Correr mantenimiento" → GitHub Actions marca el run como rojo. No se borra ni se sube nada. |

---

## Reporte semanal (#8) — futuro

`tools/notifier.py` está pensado para reusarse cuando se implemente el reporte semanal de ventas (proyecto #8 de tu lista). La interfaz es:

```
from tools.notifier import enviar_email
enviar_email("Asunto", "Cuerpo en texto plano")
```

> Si más adelante quieres notificaciones a WhatsApp (bot OpenWA) en lugar de email, agregamos otro wrapper `tools/notifier_wa.py` con la misma firma.
