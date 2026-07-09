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

---

## Análisis de temporada para fabricación (proyecto #2)

`tools/analisis_temporada.py` corre 4 queries contra la BD y entrega un panorama
completo del último año más una recomendación de cuántas unidades fabricar por
colegio × producto × talla individual — **para preparar el regreso a clases**.

### Lo que hace

1. **Panorama general** — KPIs: pedidos web, facturas POS, ingresos, abonos.
2. **Ingresos por canal y colegio** — sin duplicar facturas (cuidado con los JOIN).
3. **Top prendas × colegio × talla** — expande grupos (`6-8`, `10-12`...) a tallas individuales para que la rotación sea comparable con tu stock.
4. **Inventario actual** — agrupa por colegio × producto × talla con totales y destacados (stock bajo < 5, agotado = 0).
5. **Recomendación de fabricación** — 3 escenarios:
   - **Conservador** = `vendidas_12m × 1.00 − stock_actual`
   - **Base**       = `vendidas_12m × 1.15 − stock_actual`
   - **Optimista**  = `vendidas_12m × 1.30 − stock_actual`
   (mínimo 0 — si el stock te alcanza, no fabricues).
6. **Cruza con `backups/.last_state.json`** del weekly maintenance para mostrarte los hallazgos actuales.

### Fuentes de datos y decisiones

- **`factura_detalle` (POS)** es la fuente principal de demanda — la web aún no
  tiene peso estadístico (en el último año solo hubo 0-2 pedidos).
- Para los pedidos_web: queda listo para cuando crezca (el código tiene la
  función `expandir_venta_items` lista, solo hay que cambiar la query).
- Cruza con el catálogo de productos por colegio (helper
  `app/utils/tallas.py:expandir_grupo_para_producto`) para que las tallas del
  JSON (`"6-8"`) se repartan correctamente entre las tallas individuales
  (`6` y `8`).

### Uso

```
cd backend
python tools/analisis_temporada.py                                 # último año (default)
python tools/analisis_temporada.py --desde 2025-08-01 --hasta 2026-06-30
python tools/analisis_temporada.py --csv-dir backups/               # +CSVs exportables
python tools/analisis_temporada.py --escenarios "1.0,1.20,1.40"     # cambia los 3 escenarios
python tools/analisis_temporada.py --top 50                        # más filas en el Top
```

Sin tocar la BD: solo lee. Para automatización, lo más fácil es meterlo en
el mismo GitHub Action que ya tienes (`weekly-maintenance.yml`) o crear otro
workflow estacional.

### Importante: NO usar como única fuente para comprar tela

- Es matemática sobre lo que se vendió en los últimos 12 meses. No predice
  demanda futura — un colegio que cambia uniforme o una nueva promoción
  puede distorsionar las cifras.
- Los combinados (uniforme completo) y los pedidos por fabricación NO
  aparecen como tales aquí — se cuentan como sus piezas individuales.
- Úsalo como **una pista más**, contrastada con tu experiencia y con el
  cliente.

---

## Alertas de stock bajo (proyecto #7)

`tools/alertas_stock.py` detecta combinaciones (colegio × producto × talla)
que están **cerca de agotarse** — antes del pico de regreso a clases.

Complementa `analisis_temporada.py`:
- El análisis mira **"qué fabricar"** mirando el año pasado.
- Las alertas miran **"qué se va a acabar pronto"** mirando la velocidad
  de venta de los últimos 90 días.

### Cómo clasifica las alertas

- **CRITICA** — agotado (stock=0) si se vendió algo en 90 días. O
  ≤ 4 semanas de inventario restante.
- **ALTA** — entre 4 y 8 semanas de inventario restante.
- **MEDIA** — stock ≤ umbral sin rotación rápida (vigilar).
- **BAJA** — agotado sin ventas en 90 días (vigilar aunque no urge).

### Configuración

```
# Por CLI:
python tools/alertas_stock.py --umbral 8 --ventana 90 --csv-dir backups/

# Por .env:
MAINT_STOCK_UMBRAL=5          # default si --umbral no se pasa
MAINT_STOCK_VENTANA=90        # default días hacia atrás
```

### Notificación

- Solo envía email si hay **CRÍTICAS nuevas** o CRÍTICAS recurrentes.
- Reusa `tools/notifier.enviar_email` (Brevo).
- Estado incremental en `backups/.stock_alerts_state.json` para evitar
  spam cada lunes.
- Notificación desactivada por defecto si no hay CRÍTICAS nuevas.

### Integración con weekly maintenance

`tools/maintenance.py` ya invoca `alertas_stock` al final del flujo
semanal, así cada lunes recibes:
1. Email del mantenimiento (si hay hallazgos nuevos o backup crítico)
2. Email de alertas de stock (si hay críticas nuevas)
… en dos emails separados, cada uno con su lógica propia.

### Uso independiente

```
# Una corrida para ver qué urge:
python tools/alertas_stock.py --umbral 5 --no-notify --csv-dir backups/

# Con notificador (necesita BREVO_API_KEY + EMAIL_AVISO_TO en .env):
python tools/alertas_stock.py --umbral 5 --csv-dir backups/
```

Salida:
- **stdout** en markdown con las alertas activas (sin BAJA — están en CSV).
- **CSV** con todas las alertas (incluyendo BAJA) en
  `backups/alertas_stock_YYYY-MM-DD.csv`.

---

## Reporte semanal (proyecto #8)

`tools/reporte_semanal.py` resume la **semana anterior** (lunes-lunes)
para que sepas qué pasó sin entrar al panel. Pensado para correrlo
**automáticamente cada lunes** después del weekly maintenance, o bajo
demanda.

### Qué incluye

1. **Ventas POS por colegio** — facturas, unidades, ingresos. Origen
   `factura_detalle` (que en tu negocio es el grueso).
2. **Ventas web por colegio** — pedidos pagados.
3. **Pendientes de entrega** — agrupado por estado (POR_ENTREGAR,
   LISTO_LLAMAR, EMPACADO) + monto total.
4. **Saldos pendientes de pago** — top 20 facturas con saldo > 0 (incluye
   la **factura más vieja** sin cobrar — dime si la quieres ver primero).
5. **Abonos cobrados en la semana** — pagos recibidos.
6. **Cruzado con estado de mantenimiento** y **alertas de stock** —
   para que en un solo email veas si hay hallazgos del weekly maintenance
   o alertas activas de stock sin abrir el panel.

### Salidas

- **markdown en stdout** — bonito para leer en terminal.
- **email por Brevo** cuando no se pasa `--no-notify`.
- **CSV detallado** con `--csv-dir backups/` (todas las facturas
  pendientes y con saldo, ideal para abrir en Excel y filtrar).

### Uso

```
# Semana anterior (default)
python tools/reporte_semanal.py --csv-dir backups/

# Ventana explícita
python tools/reporte_semanal.py --desde 2025-08-04 --hasta 2025-08-10

# Sin email (solo stdout + CSV)
python tools/reporte_semanal.py --no-notify --csv-dir backups/
```

---

## Revisión de precios de uniformes completos (proyecto #4)

`tools/revisar_precios_combos.py` responde la pregunta **"¿el uniforme
completo está bien de precio comparado con la suma de piezas?"**.

Para cada (colegio, uniforme_completo, talla_grupo):

  - Calcula el **descuento implícito** que estás dando hoy
    (`1 - combo/suma_piezas`, en `%`).
  - Compara entre colegios: si la dispersión es **mayor a 3 puntos
    porcentuales**, marca INCONSISTENTE.
  - Si todo está dentro de ±3 pp, marca OK.

### Hallazgo típico (verificado contra tu BD)

Tu tienda tiene descuentos **efectivamente nulos** en los uniformes
completos (0.0 – 0.3 % sobre la suma). El combo cuesta lo mismo que las
piezas sueltas. Eso es una decisión de negocio: o le pones un descuento
real (10–15 %) o lo dejas así. El script te da los datos para decidir.

### NO MODIFICA LA BD

Es solo lectura. Las decisiones de precio las aplica **el dueño desde el
panel** (`Productos > Precios por colegio`). El script te propone el
precio "justo" según un descuento objetivo (`--descuento-meta` 0.15 =
15% sobre la suma) y tú decides si lo aplicas.

### Limitación detectada

Solo funciona donde tanto el combo como sus piezas tienen precios
configurados en `precios_colegio` para la misma talla. Si una pieza no
tiene precio en esa talla, la fila se ignora (luego completa los precios
faltantes desde el panel y vuelve a correr).

### Uso

```
# Análisis exploratorio (default: tolerancia 3 pp)
python tools/revisar_precios_combos.py --csv-dir backups

# Sugerir precios normalizados con 15% de descuento sobre la suma
python tools/revisar_precios_combos.py --descuento-meta 0.15

# Cambiar tolerancia (más estricto / más laxo)
python tools/revisar_precios_combos.py --umbral-pp 1.5
```

### Salidas

- markdown en stdout: una tabla por combo, otra con las inconsistencias
  (si las hay), y opcionalmente la propuesta de precios normalizados.
- CSV completo en `backups/revision_precios_combos_<fecha>.csv` para
  revisión en Excel.
