# RALOZ COL S.A.S — Mapa técnico del sistema

> Documento de arquitectura operativa: cómo está enlazado todo (datos, backend,
> flujos de negocio, frontend) y los problemas detectados. Generado del análisis
> del código el 2026-07-06. La versión portafolio anterior de este archivo quedó
> en el historial de git; la versión en inglés sigue en [ARCHITECTURE.md](ARCHITECTURE.md).

Piezas del sistema:

| Pieza | Tecnología | Dónde vive | Despliegue |
|---|---|---|---|
| Backend + API | Flask / SQLAlchemy / PostgreSQL (Supabase) | `backend/` | Render (auto-deploy desde main) |
| Panel admin / POS | React + Vite (migración gradual a TS) | `frontend/` | Servido por Flask desde `frontend/dist` |
| Tienda pública | HTML/CSS/JS estático + PWA | `../../Raloz/` (fuera de este repo) | Cloudflare Pages (ralozcolsas.com) |
| Bot de WhatsApp | Python (OpenWA o Meta Cloud API) | `../../whatsapp-bot/` | Corre en el PC del negocio |

---

## 1. Modelo de datos (30 tablas)

### Núcleo de ventas

```
Colegio ──┬─< PrecioColegio >── Producto      (precio por colegio+producto+talla_grupo)
          ├─< Stock >────────── Producto      (cantidad por colegio+producto+talla_individual)
          ├─< MovimientoInventario (kardex)   (ENTRADA/SALIDA/AJUSTE, stock_resultante)
          └─< Factura ─┬─< FacturaDetalle >── Producto
                       ├─< Pago
                       ├─< PrendaPendiente    (prendas vendidas sin entregar — flujo local)
                       └─< StockPendiente     (mecanismo viejo, solo lo escribe editar_factura)
Cliente >── Colegio                            (registro 360 del comprador, keyed por teléfono o email)
SerieFacturacion                               (consecutivo FAC-{año}-{n:06d})
SerieRemision                                  (definida; sin uso visible en la API)
```

### Tienda web y fabricación

```
PedidoWeb ──> Colegio (nullable: "Tienda General" p.ej. relojes)
   │  items_json (snapshot de items con tipo_pedido: normal|mixto|fabricacion|general)
   │  ──> Factura (id_factura se llena cuando MP aprueba el pago)
   ├─< PedidoFabricacion (por pedido web con items sin stock; estado en_produccion→listo_para_entrega→entregado)
Reserva ──> Colegio+Producto (retiene stock 30 min por session_id del carrito)
StockPendienteFabricacion    (acumulado por colegio+producto+talla; ids_pedidos = CSV de PedidoFabricacion ⚠ sin FK)
OrdenProduccion ──> Colegio  (órdenes al taller de confección, independiente de pedidos web)
EmpaquePendiente ──> PrendaPendiente (sin uso visible en la API actual)
```

### Operación y soporte

```
CajaDiaria ─< MovimientoCaja        (caja física: monto_inicial + ventas − gastos = esperado)
Gasto                               (estado_pago: PAGADO | PENDIENTE=deuda)
Usuario                             (roles: administrador | vendedor | cajero)
Tarea ──> Usuario (asignada/creada/completada)
Cita                                (agendadas desde la tienda/bot; sin auth para crear)
Auditoria                           (log de acciones: tabla, id, acción, detalle)
TokenRevocado                       (logout JWT)
WaConversacion ─< WaMensaje         (bandeja de WhatsApp en el panel; modo bot/humano)
```

**Convención de tallas** (`utils/tallas.py`): los **precios** se guardan por `talla_grupo`
(`6-8`, `S-M`…) y el **stock** por `talla_individual` (`6`, `8`, `S`…).
`TALLA_GRUPO_A_INDIVIDUALES` expande, `TALLA_INDIVIDUAL_A_GRUPO` colapsa.
**Excepción: las medias** — su grupo (`4-6`, `6-8`…) ES la talla y no se expande
(chocaría con los grupos de ropa).

---

## 2. Backend — blueprints (24 módulos, ~137 rutas bajo `/api`)

| Prefijo | Archivo | Qué hace | Roles de escritura |
|---|---|---|---|
| `/api/auth` | `auth.py` | Login (usuario/Google), refresh, cambiar password. Lockout 5 intentos/5 min | público |
| `/api/facturas` | `facturas.py` | CRUD factura local: consecutivo, precios autoritativos de BD, anti-sobreventa, abono inicial, conciliación con caja, upsert Cliente | adm/vend/caj (anular: adm) |
| `/api/pagos` | `pagos.py` | Pagos de saldo de facturas; editar/eliminar (adm) recalculando totales | adm/vend/caj |
| `/api/caja` | `caja.py` | Abrir/cerrar caja, movimientos manuales, historial | adm/caj |
| `/api/stock` | `stock.py` | Stock CRUD + entradas + kardex (`/movimientos`), catálogo y balance por colegio | adm/vend/caj |
| `/api/productos` | `productos.py` | Catálogo maestro + precios | adm |
| `/api/precios` | `precios.py` | PrecioColegio CRUD + bulk | adm |
| `/api/colegios` | `colegios.py` | Colegios CRUD | adm |
| `/api/clientes` | `clientes.py` | Clientes CRUD + historial de compras | cualquier autenticado |
| `/api/gastos` | `gastos.py` | Gastos y deudas (pagar deuda la convierte en gasto real) | adm/caj |
| `/api/prendas` | `prendas_pendientes.py` | Prendas vendidas pendientes de entrega (flujo local) | adm/vend |
| `/api/empaque` | `empaque.py` | Revisión/empaque local: LISTO_EMPAQUE → LISTO_LLAMAR → ENTREGADA | adm/vend |
| `/api/reportes` | `reportes.py` | Contadora, ventas, top productos, cuentas por cobrar | adm (cuentas-por-cobrar: cualquiera) |
| `/api/dashboard` | `dashboard.py` | Resumen del día/mes para la portada | autenticado |
| `/api/ventas` | `ventas.py` | Hoja de ventas diaria + resumen por método | autenticado |
| `/api/operaciones` | `operaciones.py` | Tablero unificado: prendas pendientes + fabricación + entregas | autenticado |
| `/api/usuarios` | `usuarios.py` | Gestión de usuarios | adm |
| `/api/metodos-pago` | `metodos_pago.py` | Métodos de pago CRUD | adm |
| `/api/tareas` | `tareas.py` | Tareas internas asignables | adm crea; cualquiera completa |
| `/api/citas` | `citas.py` | Citas (crear: público desde tienda/bot; gestionar: staff) | staff |
| `/api/ordenes-produccion` | `ordenes_produccion.py` | Órdenes al taller + PDF (ReportLab con logos) | adm |
| `/api/tienda` | `tienda/publico.py` | **Público**: colegios, catálogo, reservas, crear pedido (preferencia MP), pagar-saldo, webhook MP, consulta de pedido (por referencia o teléfono con token del bot) | público (rate-limited) |
| `/api/tienda/admin` | `tienda/admin.py` | Pedidos online (marcar pagado manual, generar factura, entrega) y fabricación (marcar listo/entregado, registrar saldo, stock pendiente) | adm/vend |
| `/api/wa` | `whatsapp_inbox.py` | Bandeja WhatsApp: `/log` y `/modo` para el bot (token compartido `WA_LOG_TOKEN`), resto staff. Enviar usa Graph API de Meta | staff |

**Servicios** (`app/services/`): `facturacion_web.py` (clasificar items, PedidoWeb→Factura,
PedidoFabricacion), `reconciliacion.py` (rescate de webhooks perdidos), `orden_produccion_pdf.py`,
`wa_send.py`. **Utils**: `decorators.py` (roles+auditoría), `validators.py`, `tallas.py`,
`inventario.py` (kardex), `email_service.py` (PDF en memoria + Brevo), `whatsapp_notify.py`.

**Daemons en `run.py`** (arrancan con la app): limpiar reservas vencidas (60 s),
cancelar pedidos abandonados (5 min), reconciliar pagos MP (15 min), telemetría Ducklab (3 min).
Además `_auto_migrate`: aplica `app/db_migrations.py` (14 migraciones SQL versionadas,
con advisory lock de PG para multi-worker).

---

## 3. Flujos de negocio de punta a punta

### 3.1 Venta en local (POS)

```
ENTRA: POST /api/facturas {id_colegio, cliente_*, detalles[{id_producto, talla_individual,
       cantidad, precio_unitario}], abono, metodo_pago, entrega_inmediata, domicilio, descuento}
1. Consecutivo: SerieFacturacion con SELECT FOR UPDATE → "FAC-2026-000123"
2. Precio: se ignora el del cliente si hay PrecioColegio (override queda en Auditoria)
3. Si entrega_inmediata: verifica stock (409 con faltantes si no alcanza; permitir_sobreventa lo salta)
4. Crea Factura + FacturaDetalle
   ├─ entrega_inmediata → registrar_movimiento(SALIDA) → Stock baja + kardex
   └─ si no → PrendaPendiente (queda "por entregar", SIN tocar stock)
5. abono > 0 → Pago; si es EFECTIVO y hay CajaDiaria ABIERTA → MovimientoCaja INGRESO
6. Auditoría + upsert de Cliente (por teléfono, acumula totales)
SALE: 201 {factura: to_dict_full()}   estado: PAGADA si abono cubre todo, si no PENDIENTE
7. El frontend ofrece "Imprimir ticket" → recibo 76 mm (Epson TM-U220, matriz de
   puntos, paralela → se imprime desde el PC) con empresa, ítems, totales y garantía
   (client-side, window.print; no toca backend). Reimprimible desde BuscarFacturas
```

Entrega posterior: `POST /api/prendas/<id>/entregar` (una por una) marca la PrendaPendiente
ENTREGADA. Empaque local: `/api/empaque/*` mueve `Factura.estado_entrega`:
`LISTO_EMPAQUE → LISTO_LLAMAR → ENTREGADA`.

### 3.2 Pedido web (tienda → MercadoPago → factura)

```
Cliente en ralozcolsas.com (catálogo GET /api/tienda/catalogo/<colegio>, con fallback
a Raloz/js/data/* generados si el backend duerme)
1. POST /api/tienda/reservar (por item) → Reserva 30 min por session_id
2. POST /api/tienda/pedido {cliente, items, abono_porcentaje 50|100, tipo_entrega}
   - Clasifica CADA item server-side (_clasificar_item): normal | mixto | fabricacion
     (según stock real − reservas activas de otros)
   - Precio autoritativo de PrecioColegio (relojes/"general": precio del frontend)
   - Si hay fabricación y abono 50% → total_cobrar = 50% del total
   - Crea PedidoWeb (estado=pendiente) + preferencia MP → SALE: {pago_url, referencia}
3. Cliente paga en MP → MP llama POST /api/tienda/mp/webhook
   - Valida firma HMAC (MP_WEBHOOK_SECRET); consulta el pago real a la API de MP
   - approved → pedido.estado=pagado → _crear_factura_desde_pedido():
       Factura (usuario_creacion=TIENDA_WEB, estado PAGADA o ABONO) + detalles
       + descuento de stock con FOR UPDATE re-verificando cantidades (si el stock
         se agotó entre pedido y pago → reclasifica a fabricación y actualiza items_json)
       + Pago por el monto de MP + reservas → completadas
   - Email con PDF (hilo aparte) + WhatsApp "pago confirmado" al cliente
   - _crear_pedido_fabricacion_si_aplica(): PedidoFabricacion (estado en_produccion,
     fecha estimada +60 días) + acumula StockPendienteFabricacion
   - rejected/cancelled → pedido fallido + libera reservas
   - refunded/charged_back con factura → NO toca stock; avisa al admin por WhatsApp
   - Errores → HTTP 500 para que MP reintente (idempotente: si ya hay factura, ignora)
RED DE SEGURIDAD: daemon reconciliar_pagos consulta pagos aprobados de MP (48 h)
y factura pedidos que el webhook no alcanzó. Admin también puede: marcar-pagado /
generar-factura manual en el panel.
ENTREGA: panel actualiza Factura.estado_entrega POR_ENTREGAR → EMPACADO → ENTREGADO
(con avisos de WhatsApp en cada paso).
```

### 3.3 Fabricación (prendas por encargo)

```
Nace del pedido web (items sin stock) — NO del POS local.
PedidoFabricacion: en_produccion → listo_para_entrega → entregado
StockPendienteFabricacion: agregado por (colegio, producto, talla) con CSV de pedidos.
ENTRA: POST /tienda/admin/fabricacion/stock-pendiente/registrar {id_pendiente, cantidad_fabricada}
  1. Suma la cantidad al Stock real (⚠ directo, sin kardex)
  2. Baja cantidad_pendiente; si llega a 0 → completado
  3. Para cada PedidoFabricacion del CSV: si ya no le falta nada → listo_para_entrega
marcar-listo → WhatsApp al cliente con link de pago del saldo (si debe)
Paralelo: /api/ordenes-produccion = órdenes al taller (papel/PDF), sin conexión con lo anterior.
```

### 3.4 Pagos de saldo y reconciliación

```
Saldo de factura local:  POST /api/pagos → Pago + recálculo (⚠ NO registra en caja aunque sea efectivo)
Saldo de pedido web:
  - Cliente: POST /api/tienda/pagar-saldo {referencia} → link MP "REF-SALDO"
    (solo si PedidoFabricacion está listo_para_entrega/entregado)
  - Webhook con referencia *-SALDO → _procesar_pago_saldo: idempotente por
    mp_saldo_payment_id; si el saldo ya era 0 → alerta de doble pago al admin
  - En el local: POST /tienda/admin/fabricacion/.../registrar-saldo → Pago + baja
    saldo en Factura y PedidoFabricacion (⚠ tampoco toca caja)
Reconciliación: daemon cada 15 min → GET /v1/payments/search de MP (aprobados 48h)
→ pedidos RALOZ-* sin factura se facturan (los *-SALDO no se reconcilian).
```

### 3.5 Bot de WhatsApp

Dos transportes con la misma lógica (`responses.py`): `bot.py` (OpenWA local con QR)
y `bot_meta.py` (Meta Cloud API oficial). Consumen del backend:
`/api/tienda/colegios`, `/api/tienda/catalogo/<id>` (precios/stock en vivo),
`/api/tienda/pedidos-por-telefono/<tel>` (con header `X-Bot-Token` = `WA_LOG_TOKEN`),
`/api/tienda/pagar-saldo`, `/api/citas/nueva`. Loguea conversaciones en `/api/wa/log`
y consulta `/api/wa/modo/<chat>` (bot vs humano). El backend a su vez notifica a
clientes vía `utils/whatsapp_notify.py` → Graph API de Meta.

---

## 4. Frontend (panel admin)

`services/api.ts`: axios con base `/api`, Bearer automático, refresh en 401, redirect a login.
`AuthContext`: JWT en localStorage, `isAdmin()/isVendedor()/isCajero()`.

**PWA (app instalable):** el panel se instala en el celular (standalone, sin tienda de apps) desde `raloz-web.onrender.com`. Archivos en `frontend/public/`: `manifest.webmanifest` (shortcuts a Vender/Facturas/WhatsApp/Stock/Gastos/Reportes) + `sw.js` + íconos. El service worker **nunca cachea `/api/*`** (JWT/datos en vivo); navegaciones red-primero, assets cache-primero; subir `CACHE_VERSION` para forzar update. Se registra en `main.jsx` solo en producción y recarga solo al activar una versión nueva. Flask sirve `sw.js`/manifest como archivos reales (catch-all comprueba `os.path.isfile`).

**Ticket POS:** tras crear una venta, `Facturacion.jsx › imprimirRecibo()` abre una ventana de impresión con layout **76 mm** (impresora **Epson TM-U220PD / M188D**: matriz de puntos, papel 76mm, **interfaz paralela LPT**): datos de empresa (`localStorage.raloz_empresa`), ítems, totales/abono/saldo y términos de garantía. Al ser **paralela se imprime desde el computador** (driver de Windows), NO desde el celular. `BuscarFacturas.jsx › imprimirTicket()` reimprime el mismo ticket 76mm desde una factura guardada (para ventas hechas en el celular o reimpresos). Es distinto del PDF de factura que se manda por correo (ese va por el webhook con ReportLab).

| Ruta | Componente | Endpoints que usa | Rol |
|---|---|---|---|
| `/` | Dashboard | `/dashboard/resumen` | todos |
| `/facturacion` | Facturacion | `/colegios /productos /precios /facturas` | todos |
| `/buscar` | BuscarFacturas | `/facturas* /pagos* /prendas/<id>/entregar` | todos |
| `/pagos` | Pagos | `/facturas /pagos*` | todos |
| `/stock` | StockView | `/stock*` (resumen, actividad, catálogo, balance, entrada) | todos |
| `/ventas` | Ventas | `/ventas/hoja` | todos |
| `/clientes` | Clientes | `/clientes*` | todos |
| `/gastos` | Gastos | `/gastos*` | adm, caj |
| `/caja` | Caja | `/caja/*` | adm, caj |
| `/pendientes` | Pendientes | `/prendas*` ⚠ usa `/prendas/entregar-batch` que NO existe | todos |
| `/empaque` | Empaque | `/empaque/*` `/prendas` | todos |
| `/precios` | Precios | `/precios* /colegios /productos` | adm |
| `/cuentas` | CuentasPorCobrar | `/reportes/cuentas-por-cobrar` | todos |
| `/reportes` | Reportes | `/reportes/* /gastos` | adm |
| `/configuracion` | Configuracion | `/colegios /productos /metodos-pago /usuarios` | adm |
| `/usuarios` | Usuarios | `/usuarios*` | adm |
| `/whatsapp` | WhatsApp | `/wa/*` | todos |
| `/citas` | Citas | `/citas*` | todos |
| `/tareas` | Tareas | `/tareas*` | todos |
| `/operaciones` | Operaciones.tsx (tabs: CentroOperaciones + PedidosOnline + PedidosFabricacion + StockPendienteFab) | `/operaciones/tablero /tienda/admin/*` | todos |
| `/pedidos-online` | PedidosOnline | `/tienda/admin/pedidos*` | todos |
| `/fabricacion` | PedidosFabricacion | `/tienda/admin/fabricacion/*` | todos |
| `/fabricacion/stock` | StockPendienteFab | `/tienda/admin/fabricacion/stock-pendiente*` | todos |
| `/ordenes-produccion` | OrdenesProduccion | `/ordenes-produccion*` | adm |

`Layout.jsx` sondea los badges: `/citas/pendientes/conteo`, `/tienda/admin/pedidos/conteo-nuevos`, `/wa/no-leidos`.

Nota: varias rutas son "todos" en el router pero el backend igual exige rol en la
escritura (p. ej. un cajero puede VER pedidos online pero el POST le da 403).

---

## 5. Problemas detectados

> **Actualización Fase 2 (2026-07-06):** corregidos A1 (entregar-batch), A2 (estado
> 'listo'), A3 (precios Adventista = suma de piezas), B completo (kardex en los 4
> flujos + devoluciones por neto real + resincronización histórica), C (pagos de
> saldo en efectivo entran a caja), la duplicación E de recálculo/tallas/consecutivo,
> y el webhook de saldo ahora crea el registro de Pago. Los datos huérfanos y las
> 13 facturas descuadradas se repararon con `tools/reparar_datos_fase2.py`
> (auditado; respaldo previo). Pendientes: unificar vocabulario de estados (D, se
> puenteó en lectura), upsert de Cliente unificado, y `editar_factura` sigue sin
> considerar domicilio/descuento al recalcular el total. Factura R-716 tiene
> sobrepago de $35.800 — revisar devolución con el cliente.

### A. Bugs (comportamiento roto hoy)

| # | Problema | Dónde | Efecto |
|---|---|---|---|
| A1 | El frontend llama `POST /api/prendas/entregar-batch` y **el endpoint no existe** | `Pendientes.jsx:96` | El botón de entrega masiva de prendas devuelve 404 |
| A2 | `_estado_pedido_texto` compara `pf.estado == 'listo'`, pero los estados reales son `listo_para_entrega`/`entregado` | `tienda/publico.py:930` (y el campo `listo` del cambio sin commitear usa lo mismo) | El cliente/bot nunca ve "✅ Listo para entrega" aunque su pedido lo esté |
| A3 | Uniforme COMPLETO Niña del Adventista tallas S/M/L/XL cuesta **$9.500–$16.000 MÁS** que la suma de sus piezas | Datos (PrecioColegio) | Cliente que compra el paquete paga de más; el resto de completos tiene descuentos irregulares (−500 a −1.500) |

### B. Inventario — el kardex se puede desincronizar

`utils/inventario.registrar_movimiento()` se declara como "el ÚNICO lugar donde se
cambia el stock", pero lo saltan **4 flujos** que tocan `Stock.cantidad` directo (sin
dejar rastro en MovimientoInventario):

1. `facturas.editar_factura` (devuelve y descuenta stock a mano)
2. `facturas.anular_factura` (devuelve stock)
3. `facturacion_web._crear_factura_desde_pedido` (ventas web — ninguna venta online queda en el kardex)
4. `tienda/admin.registrar_fabricacion` (entrada de prendas fabricadas)

Consecuencia: el "Balance por colegio" (`/api/stock/balance`, calculado desde el kardex)
no cuadra con el stock real.

Además: **anular/editar factura devuelven stock aunque nunca se descontó** — si la
venta fue "por entregar" (PrendaPendiente), el stock no bajó al vender, pero al anular
sí sube → inventario inflado.

### C. Caja — pagos de saldo en efectivo no entran

Solo el **abono inicial** de `crear_factura` registra MovimientoCaja. Un pago de saldo
en efectivo por `/api/pagos` o `/tienda/admin/.../registrar-saldo` **no toca la caja**
→ al cerrar caja la diferencia da negativa sin que sea un faltante real.

### D. Estados con dos vocabularios

`Factura.estado_entrega` mezcla el flujo local (`POR_ENTREGAR → LISTO_EMPAQUE →
LISTO_LLAMAR → ENTREGADA`) con el web (`POR_ENTREGAR → EMPACADO → ENTREGADO`).
`ENTREGADA` ≠ `ENTREGADO`. Efectos: un pedido web procesado con el módulo de empaque
local desaparece de la vista "activos" de pedidos online (solo filtra
POR_ENTREGAR/EMPACADO); los textos del bot solo mapean el vocabulario web.
`Factura.estado` también tiene doble forma para lo mismo: `PENDIENTE` (local) vs
`ABONO` (web) para facturas parcialmente pagadas.

### E. Lógica duplicada (misma regla en dos sitios que ya divergieron)

| Qué | Copia 1 | Copia 2 | Divergencia |
|---|---|---|---|
| Consecutivo de factura | `facturas.crear_factura` (FOR UPDATE, formato fijo) | `facturacion_web` (sin lock, usa `serie.formato`) | La web puede duplicar consecutivo en carrera con el POS |
| Recalcular totales/estado de factura | `pagos._recalcular_factura` | inline en `facturas.editar/reactivar`, `tienda/admin.registrar_saldo`, `publico._procesar_pago_saldo` | Reglas de estado ligeramente distintas |
| Upsert de Cliente | `facturas._upsert_cliente_venta` (clave: teléfono) | `facturacion_web` (clave: email→documento) | El mismo comprador queda duplicado entre canal local y web |
| Expansión de tallas + regla de medias | `inventario.construir_catalogo_colegio` | `publico.catalogo_colegio` | Dos listas de orden de tallas distintas (`_TALLA_ORDEN` vs `_ORDEN_TALLAS`) |
| Total con domicilio/descuento | `crear_factura` (subtotal − descuento + domicilio) | `editar_factura` (total = suma de líneas, **pierde domicilio y descuento**) | Editar una factura con domicilio corrige mal el total |

### F. Datos por diagnosticar en la BD (script propuesto, solo lectura)

- `StockPendiente`: tabla del mecanismo viejo; probablemente filas huérfanas apuntando
  a facturas editadas/anuladas. Solo la escribe `editar_factura`; nadie la "cierra".
- `StockPendienteFabricacion.ids_pedidos`: CSV sin FK → puede referenciar
  PedidoFabricacion borrados.
- Facturas cuyo `total_abonado` ≠ suma real de `pagos` (por los caminos que actualizan
  a mano).
- Estados fuera de vocabulario en `estado_entrega`.

### G. Menores

- `app/__init__.py:180`: línea comentada `[ARCHIVED] pendientes_bp` referencia un módulo que ya no existe.
- `PedidoWeb.wompi_status`: nombre legado de la pasarela Wompi guardando estados de MercadoPago.
- `empaque.obtener_factura_empaque` busca con `ilike '%num%'`: "123" puede traer la factura equivocada.
- `EmpaquePendiente` y `SerieRemision`: modelos sin uso visible en la API.
- Tests (103) cubren bien tienda/webhook/reservas/inventario/migraciones, pero **no hay
  ninguno del flujo POS local** (crear/editar/anular factura, pagos, caja).
