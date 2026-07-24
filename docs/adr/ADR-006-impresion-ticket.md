# ADR-006: Impresión del ticket de venta client-side (76 mm), desde el PC

**Status:** Accepted
**Date:** 2026-07-17
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

Se necesita imprimir un **recibo** tras cada venta con datos de empresa, ítems, totales y términos de garantía. La impresora de la taquilla resultó ser una **Epson TM-U220PD (M188D)**: matriz de puntos, papel **76 mm**, **interfaz paralela (LPT)**, conectada al **computador** por un adaptador paralelo→USB. Julian llegó a descargar dos SDKs de Epson (ePOS SDK JavaScript y JavaPOS ADK) buscando cómo imprimir.

## Decision

Generar el ticket **en el navegador (client-side)** con `window.open` + `window.print()` y CSS `@page { size: 76mm auto }`, e imprimirlo **desde el PC** con el driver de Windows de Epson (APD). El mismo ticket se puede **reimprimir desde Buscar Facturas** (`imprimirTicket`), lo que permite vender en el celular y luego imprimir en la taquilla, o reimprimir si el cliente lo pierde. Se descartan ambos SDKs de Epson.

## Options Considered

### Opción A: `window.print()` client-side a 76 mm (elegida)
**Pros:** cero dependencias; funciona con cualquier impresora instalada en Windows (incluida la paralela); reimprimible desde cualquier factura; sin backend.
**Cons:** pasa por el diálogo de impresión del navegador; sin control fino de corte/cajón; formato limitado a lo que renderiza el navegador.

### Opción B: Epson ePOS SDK for JavaScript
**Pros:** control ESC/POS (corte, cajón monedero), imprimir desde el celular por red.
**Cons:** **solo soporta impresoras por LAN/WiFi** (se conecta a la IP de la impresora). La TM-U220PD es **paralela** → el SDK no puede comunicarse con ella. Inviable con el hardware actual.

### Opción C: Epson JavaPOS ADK
**Pros:** soporta todas las interfaces (incl. paralela).
**Cons:** es para aplicaciones **Java de escritorio**, no para una web/React. No se integra con el panel.

## Trade-off Analysis

El hardware (impresora **paralela**) descarta de entrada las dos vías "avanzadas": ePOS-JS exige impresora de **red** y JavaPOS exige app **Java**. `window.print()` (A) es la única que funciona con lo que hay, es la más simple y no añade dependencias. El precio a pagar (sin corte/cajón automáticos y depender del diálogo del navegador) es aceptable para el volumen y el presupuesto. Las opciones B/C solo tendrían sentido si en el futuro se compra una **Epson de red**.

## Consequences

- ✅ **Más fácil:** imprime hoy con el hardware actual; reimpresión trivial desde cualquier factura; sin costo ni infraestructura.
- ⚠️ **A vigilar:** requiere el **driver APD** instalado en el PC y el papel configurado a 76 mm; no se puede imprimir directo desde el celular (la impresora es paralela) → se imprime desde el PC.
- 🔁 **A revisitar si:** se adquiere una impresora Epson con **Ethernet/WiFi** → integrar el ePOS SDK for JavaScript para imprimir desde el celular con corte y cajón automáticos.

## Action Items

1. [x] `imprimirRecibo()` en `Facturacion.jsx` / `Vender.jsx` con layout 76 mm.
2. [x] `imprimirTicket()` en `BuscarFacturas.jsx` para reimprimir desde una factura guardada.
3. [ ] Usuario: instalar driver APD en el PC de la taquilla y fijar papel a 76 mm.
