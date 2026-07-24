# ADR-003: Nueva Venta visual (`/vender`) al lado del formulario clásico

**Status:** Accepted
**Date:** 2026-07-20
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

Los mockups "Mejora del sistema POS" proponen un **Nueva Venta visual**: grid de prendas **con foto**, pestañas por colegio y carrito, en vez del formulario actual (`/facturacion`) basado en listas desplegables. Restricción crítica: `/facturacion` es el **flujo de venta que se usa a diario** — romperlo detiene el negocio. Además, la pantalla nueva no se puede verificar end-to-end sin login/backend en vivo.

## Decision

Construir la venta visual como **ruta nueva `/vender`**, reutilizando exactamente los mismos endpoints y payload que `/facturacion` (`/colegios`, `/productos`, `/precios`, `POST /facturas`, manejo de sobreventa 409), y **dejar `/facturacion` intacto como respaldo**. Tras validar, **unificar el menú** a una sola "Nueva Venta" que apunta a `/vender`, dejando el clásico fuera del menú (accesible por enlace "Modo clásico").

## Options Considered

### Opción A: Pantalla nueva aparte + respaldo (elegida)
**Pros:** cero riesgo para el flujo diario; se puede probar en producción con el clásico como red de seguridad; migración gradual.
**Cons:** dos pantallas coexisten un tiempo; algo de código duplicado (el ticket, la lógica de precios).

### Opción B: Reemplazar `/facturacion` directamente
**Pros:** más simple, sin duplicación.
**Cons:** si algo falla, se cae la venta del día; imposible de verificar sin login desde el entorno de desarrollo.

### Opción C: Solo preparar las fotos primero, sin UI
**Pros:** avance seguro.
**Cons:** no entrega valor visible todavía.

## Trade-off Analysis

El eje es **riesgo al flujo crítico vs. simplicidad**. Como no había forma de verificar la venta visual end-to-end antes de desplegar, reemplazar directo (B) era una apuesta contra el ingreso diario. A cambio de una duplicación temporal, A permite desplegar sin miedo y revertir con un toque. La unificación del menú se hizo *después*, cuando la nueva ya estaba disponible, manteniendo el clásico como salvavidas oculto.

## Consequences

- ✅ **Más fácil:** experiencia de venta moderna en móvil; migración sin downtime; rollback inmediato.
- ⚠️ **A vigilar:** mantener dos caminos de venta hasta jubilar el clásico; el grid depende de que existan fotos por prenda (ver [ADR-004](ADR-004-fotos-producto-estaticas.md)).
- 🔁 **A revisitar si:** `/vender` demuestra ser estable en ventas reales → retirar `/facturacion`.

## Action Items

1. [x] `components/facturacion/Vender.jsx` en ruta `/vender`, reusando endpoints de Facturacion.
2. [x] Barra inferior y menú apuntan a `/vender`; enlace "Modo clásico" a `/facturacion`.
3. [ ] Validar con ventas reales (fotos, precios por talla, guardado) — pendiente del usuario.
4. [ ] Cuando esté probado, retirar del código el clásico si ya no se usa.
