# RALOZ COL SAS — Simulador de Flujos de Compra

> Este documento simula paso a paso qué ocurre en cada escenario de compra:
> qué ve el cliente, qué hace el sistema, qué ve el vendedor en el POS.

---

## Escenarios disponibles

| # | Escenario | Tipo | Pago |
|---|-----------|------|------|
| A | Compra normal de stock (uniforme disponible) | Normal | 100% |
| B | Pedido bajo fabricación (sin stock) | Fabricación | 50% abono |
| C | Pedido mixto (parte stock + parte fabricación) | Mixto | 50% abono |
| D | Fabricación con pago completo (100%) | Fabricación | 100% |
| E | Pago fallido / rechazado | Cualquiera | — |
| F | Vendedor registra venta en mostrador (no web) | Mostrador | Efectivo |

---

---

## 🟢 ESCENARIO A — Compra normal de stock

**Situación:** Una madre compra 2 camisas para su hijo en el Colegio Marillac. Las camisas están en stock.

### Lo que hace el cliente en la tienda (ralozcolsas.com)

```
1. Abre la tienda → selecciona "Colegio Marillac"
2. Ve el catálogo → selecciona "Camisa Niño"
3. Elige talla 10 → el sistema muestra "3 disponibles · Entrega inmediata"
4. Cantidad: 2 → "Agregar al carrito"
5. Abre el carrito → ve subtotal $80.000
6. Clic "Ir a pagar" → aparece el formulario de checkout
7. Llena: Nombre, email, teléfono, dirección (opcional)
   (No aparece opción de abono porque no hay fabricación)
8. Clic "Ir a pagar con MercadoPago" → redirige a checkout.mercadopago.com
9. Paga con tarjeta débito Bancolombia → transacción aprobada
10. MercadoPago redirige a ralozcolsas.com?status=success
```

### Lo que hace el sistema (automático, en segundos)

```
PASO 1 — Crear pedido (POST /api/tienda/pedido)
  ├── Valida stock: Camisa Niño T.10 tiene 3 unidades → OK
  ├── Crea reserva temporal (15 min) → Reserva #45
  ├── Crea PedidoWeb:
  │     referencia: "RALOZ-F3A8B2C1D9E0"
  │     estado: 'pendiente'
  │     total: $80.000
  │     abono_porcentaje: 100
  │     tiene_fabricacion: false
  └── Genera preferencia MP → retorna pago_url

PASO 2 — Cliente paga en MercadoPago

PASO 3 — Webhook llega (POST /api/tienda/mp/webhook)
  ├── MP confirma: status = 'approved'
  ├── Actualiza PedidoWeb.estado = 'pagado'
  ├── Crea Factura FAC-2026-000042:
  │     estado: 'PAGADA'
  │     total: $80.000
  │     total_abonado: $80.000
  │     saldo_pendiente: $0
  │     estado_entrega: 'POR_ENTREGAR'
  ├── Descuenta stock:
  │     Camisa Niño T.10 Marillac: 3 → 1 (descuenta 2)
  ├── Marca Reserva #45: 'completada'
  ├── Crea Pago: $80.000 / tarjeta-debito / TIENDA_WEB
  └── Envía email con PDF FAC-2026-000042 a cliente@email.com
```

### Lo que ve el vendedor en el POS

**En `/pedidos-online`:**
```
┌─────────────────────────────────────────────────────────┐
│ RALOZ-F3A8B2C1D9E0  │  14/04/2026  │  María García     │
│ Marillac            │  $80.000     │  ✅ Pagado         │
│                                    │  📦 Por entregar   │
│  [👁 Ver]  [⬇ PDF]  [📦 Empacar]              │
└─────────────────────────────────────────────────────────┘
```

**Flujo de entrega del vendedor:**
```
1. Clic "📦 Empacar" → badge cambia a 🎁 Empacado
2. Prepara el paquete físicamente
3. Cuando el cliente recoge → clic "🚚 Marcar Entregado"
4. badge cambia a ✅ Entregado
5. Factura queda en estado_entrega = 'ENTREGADO'
```

**En `/stock` el vendedor ve:**
```
Camisa Niño — Talla 10 — Marillac: 1 unidad (antes 3)
```

**Estado final de objetos en BD:**
```
PedidoWeb.estado          = 'pagado'
Factura.estado            = 'PAGADA'
Factura.estado_entrega    = 'ENTREGADO'  (después del proceso)
Stock (Camisa T.10)       = 1  (descontado)
Reserva #45               = 'completada'
```

---

---

## 🟡 ESCENARIO B — Pedido bajo fabricación (sin stock)

**Situación:** Un padre quiere uniformes del Colegio Adventista pero no hay stock. Los uniformes se fabrican bajo pedido. Paga el 50% de abono.

### Lo que hace el cliente

```
1. Selecciona "Colegio Adventista"
2. Ve productos → "Pantalón Niño" muestra "🪡 Bajo pedido · Entrega en 1-2 meses"
3. Elige talla 12 → cantidad 1 → "Agregar pedido anticipado"
4. También agrega "Camisa Niña" T.8 bajo pedido
5. Carrito muestra: 2 items 🪡, subtotal $120.000
6. Checkout → aparece selector de abono:
   ┌─────────────────────────────────────────────┐
   │ 🪡 Tienes $120.000 en prendas por fabricar  │
   │ ┌──────────────────────┐  ┌───────────────┐ │
   │ │ ✓ Abono 50%          │  │  Pago total   │ │
   │ │ $60.000 ahora        │  │  $120.000     │ │
   │ │ $60.000 al recoger   │  │  ahora        │ │
   │ └──────────────────────┘  └───────────────┘ │
   └─────────────────────────────────────────────┘
   Total a pagar ahora: $60.000
7. Selecciona "Abono 50%" → paga $60.000 en MercadoPago
```

### Lo que hace el sistema

```
PASO 1 — Crear pedido
  ├── tipo_pedido: 'fabricacion' → NO valida stock
  ├── Crea PedidoWeb:
  │     total: $60.000  (solo el abono)
  │     total_orden: $120.000  (valor real)
  │     abono_porcentaje: 50
  │     tiene_fabricacion: true
  └── Genera preferencia MP por $60.000

PASO 2 — Webhook aprobado
  ├── Crea Factura FAC-2026-000043:
  │     total: $120.000  (valor real del pedido)
  │     total_abonado: $60.000  (lo que pagó)
  │     saldo_pendiente: $60.000  (lo que falta)
  │     estado: 'ABONO'  ← no es PAGADA porque hay saldo
  │     observaciones: "Pedido web RALOZ-xxx [INCLUYE PEDIDO POR FABRICACIÓN]"
  ├── Stock: NO se descuenta (los items son de fabricación)
  ├── Crea PedidoFabricacion #12:
  │     estado: 'en_produccion'
  │     abono_monto: $60.000
  │     saldo_pendiente: $60.000
  │     items: [{Pantalón T.12, fabricacion}, {Camisa T.8, fabricacion}]
  │     fecha_estimada: 45 días desde hoy
  └── Crea StockPendienteFabricacion:
        Pantalón Niño T.12 Adventista: +1 pendiente
        Camisa Niña T.8 Adventista:   +1 pendiente
```

### Lo que ve el vendedor en el POS

**En `/pedidos-online`:**
```
┌──────────────────────────────────────────────────────┐
│ RALOZ-xxx  │  14/04/2026  │  Carlos Pérez            │
│ Adventista │  $120.000    │  ✅ Pagado               │
│                           │  📦 Por entregar         │
│  🏭 Incluye fabricación                              │
│  [👁 Ver detalle]   [⬇ PDF]                         │
└──────────────────────────────────────────────────────┘
```

**El PDF que recibió el cliente muestra:**
```
FACTURA N° FAC-2026-000043
Total del pedido:        $120.000
Abono pagado hoy:        $60.000  ✅ (verde)
Saldo pendiente al recoger: $60.000  🔴 (rojo)
```

**En `/fabricacion` el vendedor sigue el proceso:**
```
┌─────────────────────────────────────────────────────┐
│ #12  🏭 En producción   Carlos Pérez  Adventista     │
│      Abono: $60.000 | Saldo: $60.000                │
│  [▼ Expandir]                                        │
│                                                      │
│  ExpandidO:                                          │
│  ┌─────────────────────────────────────────────┐    │
│  │ Pantalón Niño  T.12  ×1  🏭 Fabricar        │    │
│  │ Camisa Niña    T.8   ×1  🏭 Fabricar        │    │
│  └─────────────────────────────────────────────┘    │
│  Total: $120.000 | Abono: $60.000 | Saldo: $60.000  │
│                                                      │
│  Fecha estimada: 28/05/2026  [Editar]               │
│                                                      │
│  [✅ Marcar listo para entrega]                      │
└─────────────────────────────────────────────────────┘
```

**Cuando el pedido está listo para entregar:**
```
Vendedor clic "✅ Marcar listo para entrega"
  → estado cambia a 'listo_para_entrega'

Aparecen nuevos botones:
  [💬 Notificar por WhatsApp]
  [💰 Registrar pago saldo]
  [📦 Marcar entregado]

Clic "💬 Notificar por WhatsApp" → abre:
  wa.me/573101234567?text=Hola Carlos Pérez, su pedido RALOZ #12
  está listo para entrega esta semana. Debe cancelar el saldo
  de $60.000 para coordinar la entrega. ¡Contáctenos! 🎒

Cliente llega a recoger y paga $60.000 en efectivo:
  Clic "💰 Registrar pago saldo"
  → Modal: monto=$60.000, método=efectivo
  → Confirmar
  → saldo_pendiente = 0
  → Factura.estado = 'PAGADA'

Clic "📦 Marcar entregado"
  → PedidoFabricacion.estado = 'entregado'
```

**Estado final:**
```
PedidoWeb.estado             = 'pagado'
Factura.estado               = 'PAGADA'  (después del saldo)
Factura.saldo_pendiente      = 0
PedidoFabricacion.estado     = 'entregado'
StockPendienteFabricacion    = pendiente → (se marca completo)
Stock real                   = sin cambio (era fabricación)
```

---

---

## 🔵 ESCENARIO C — Pedido mixto (parte stock + parte fabricación)

**Situación:** Una madre pide 3 camisas talla 10 para el Colegio Marillac. Hay 2 en stock pero 1 hay que fabricarla.

### Lo que ve el cliente al agregar al carrito

```
Sistema detecta: cantidad 3 > stock disponible 2
→ Agrega item como 'mixto':
   stock_disponible: 2
   cantidad_total: 3
   (3 - 2 = 1 por fabricación)

En carrito se ve:
   "Camisa Niño T.10 ×3 (2 inmediato + 1 🪡)"

En checkout aparece doble selector:
   ┌──────────────────────────────────────────────────┐
   │ 🔀 Tienes 2 unidades disponibles y 1 por fabricar │
   │ ¿Cómo las quieres recibir?                        │
   │  ✓ Recibir por partes   │  Esperar todo junto      │
   └──────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────┐
   │ 🪡 $15.000 en prendas por fabricar               │
   │  ✓ Abono 50%            │  Pago total             │
   │  $32.500 ahora          │  $45.000 ahora          │
   │  $7.500 al recoger      │                         │
   └──────────────────────────────────────────────────┘
   (precio unitario: $15.000. 2×$15.000=$30.000 inmediato
    1×$15.000=$15.000 fabricación → abono 50% = $7.500)
   Total a pagar ahora: $30.000 + $7.500 = $37.500
```

### Lo que hace el sistema

```
PASO 1 — Crear pedido
  ├── items: [{tipo_pedido: 'mixto', stock_disponible: 2, cantidad: 3}]
  ├── total_cobrar: $30.000 (2 inmediatas) + $7.500 (50% de $15.000) = $37.500
  ├── total_orden: $45.000
  └── tiene_fabricacion: true

PASO 3 — Crear factura
  ├── Para item mixto:
  │     Descuenta stock: 2 unidades (stock_disponible)
  │     La 3ra unidad va a fabricación
  ├── Factura:
  │     total: $45.000
  │     total_abonado: $37.500
  │     saldo_pendiente: $7.500
  │     estado: 'ABONO'
  └── PedidoFabricacion con 1 camisa T.10

PASO 4 — StockPendienteFabricacion
  ├── Camisa Niño T.10 Marillac: +1 pendiente fabricar
  └── Stock real Camisa T.10: 2 → 0 (descontó las 2 de stock)
```

### Lo que ve el vendedor

**En `/pedidos-online`:**
```
Items con badge:
  Camisa Niño T.10 ×3   Mixto   $45.000
  (2 salieron de stock, 1 va a fabricación)
```

**En `/fabricacion`:**
```
#15  🏭 En producción
  Camisa Niño T.10 ×1  🏭 Fabricar
  Saldo pendiente: $7.500
```

**Flujo:**
```
1. Las 2 camisas de stock se pueden empacar y entregar inmediatamente
   (si cliente eligió "Recibir por partes")
2. Cuando esté lista la camisa fabricada:
   → Marcar listo → Notificar WhatsApp → Registrar pago $7.500 → Entregar
```

---

---

## 🟣 ESCENARIO D — Fabricación con pago completo (100%)

**Situación:** Un cliente prefiere pagar todo ahora en lugar de abonar el 50%.

```
Cliente selecciona "Pago total" en el checkout
→ Paga $120.000 completo

Sistema:
  PedidoWeb.abono_porcentaje = 100
  Factura.total_abonado      = $120.000
  Factura.saldo_pendiente    = $0
  Factura.estado             = 'PAGADA'  (no 'ABONO')
  PedidoFabricacion.saldo_pendiente = $0

El PDF que recibe el cliente:
  TOTAL PAGADO: $120.000  ← caja oscura con total en amber (sin desglose de saldo)

En /fabricacion el vendedor ve:
  Saldo: ✓ Saldado  (verde, no rojo)

Cuando esté listo el pedido:
  [💬 Notificar por WhatsApp] → mensaje sin mención de saldo:
  "su pedido está listo. Todo está pagado, coordinaremos la entrega pronto 🎒"
  [📦 Marcar entregado]  ← no aparece botón de "Registrar pago"
```

---

---

## 🔴 ESCENARIO E — Pago fallido o rechazado

**Situación:** El cliente intenta pagar pero la tarjeta es rechazada.

```
1. POST /api/tienda/pedido → crea PedidoWeb con estado='pendiente'
2. Cliente ingresa datos en MercadoPago → tarjeta rechazada
3. MercadoPago envía webhook con status='rejected'

Sistema al recibir webhook rejected:
  ├── PedidoWeb.estado = 'fallido'
  ├── Libera reservas activas: Reserva.estado = 'cancelada'
  ├── Stock NO fue descontado (nunca se descuenta hasta pago aprobado)
  └── NO se crea Factura, NO se envía email

En /pedidos-online el vendedor ve:
  RALOZ-xxx  │  ❌ Fallido  │  (sin badge de entrega)
  
  El vendedor puede:
  → Contactar al cliente por WhatsApp para reintentar
  → Si el cliente viene a la tienda: crear venta manual en /facturacion
```

---

---

## 🏪 ESCENARIO F — Venta en mostrador (sin web)

**Situación:** Un cliente llega físicamente a la tienda y compra en efectivo. El vendedor usa el POS directamente.

### El vendedor en `/facturacion`

```
1. Selecciona colegio: "Marillac"
2. Agrega productos al carrito del POS:
   └── Camisa Niño T.10 × 2 → $80.000
3. Datos del cliente: nombre, teléfono (email opcional)
4. Método de pago: Efectivo
5. Clic "Facturar" → se crea directamente:
   ├── Factura FAC-2026-000044
   │     estado: 'PAGADA'
   │     canal: 'MOSTRADOR'  (no WEB)
   │     estado_entrega: 'POR_ENTREGAR'
   ├── FacturaDetalle × 1 línea
   ├── Pago: $80.000 / EFECTIVO
   └── Stock: Camisa T.10 Marillac: 3 → 1
```

### Diferencias clave con venta web

| | Venta Web | Venta Mostrador |
|--|-----------|-----------------|
| Flujo pago | MercadoPago → webhook | Directo en POS |
| Creación factura | Automática al aprobar pago | Inmediata al facturar |
| Email al cliente | Automático con PDF | No (a menos que vendedor lo envíe) |
| PedidoWeb | ✅ Creado | ❌ No existe |
| Canal en factura | `WEB` | `MOSTRADOR` |
| Aparece en /pedidos-online | ✅ Sí | ❌ No |
| Aparece en /buscar | ✅ Sí | ✅ Sí |

---

---

## 📊 Resumen: Estados del Sistema por Escenario

### PedidoWeb

| Evento | estado |
|--------|--------|
| Pedido creado en tienda | `pendiente` |
| Pago aprobado por MP | `pagado` |
| Pago rechazado/cancelado | `fallido` |
| Saldo de fabricación pagado | sigue `pagado` (el estado no cambia) |

### Factura

| Situación | estado | estado_entrega |
|-----------|--------|----------------|
| Pago 100% aprobado | `PAGADA` | `POR_ENTREGAR` |
| Pago 50% abono aprobado | `ABONO` | `POR_ENTREGAR` |
| Vendedor empaca | sin cambio | `EMPACADO` |
| Vendedor entrega | sin cambio | `ENTREGADO` |
| Saldo cobrado | `PAGADA` | sin cambio |
| Anulada manualmente | `ANULADA` | sin cambio |

### PedidoFabricacion

| Evento | estado |
|--------|--------|
| Creado al aprobar pago | `en_produccion` |
| Vendedor termina fabricación | `listo_para_entrega` |
| Vendedor entrega al cliente | `entregado` |

### Stock

| Evento | Efecto |
|--------|--------|
| Pago aprobado (item normal) | stock -= cantidad |
| Pago aprobado (item mixto) | stock -= stock_disponible |
| Pago aprobado (item fabricación) | sin cambio |
| Pago rechazado | sin cambio |
| Ajuste manual en /stock | stock += o -= ajuste |

---

---

## 🔍 Cómo verificar cada paso en el POS

### Ver pedidos web recientes
```
/pedidos-online → tabla de todos los pedidos
Filtros: Pendientes / Pagados / Fallidos
```

### Ver qué hay que fabricar
```
/fabricacion → cards por pedido
Filtros: En Producción / Listo para Entrega / Entregado
```

### Ver stock actual
```
/stock → tabla por colegio + producto + talla
Click en producto → historial de movimientos
```

### Ver prendas pendientes de fabricar (total)
```
/fabricacion/stock → agrupado por colegio/producto/talla
Cuántas unidades están pendientes en total
```

### Ver cuentas por cobrar (saldos pendientes)
```
/cuentas → facturas con saldo_pendiente > 0
```

### Ver si llegó el email al cliente
```
Render logs → buscar "[EMAIL-BREVO] Factura FAC-xxx enviada a email@..."
```

### Registrar saldo de fabricación pagado
```
/fabricacion → abrir card del pedido → "💰 Registrar pago saldo"
→ Ingresar monto + método → Confirmar
→ Factura pasa a estado PAGADA automáticamente
```

---

*Documento generado para el equipo RALOZ COL SAS — Bogotá, Colombia*
