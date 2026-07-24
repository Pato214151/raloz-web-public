# ADR-002: Panel administrativo como PWA instalable (no app nativa)

**Status:** Accepted
**Date:** 2026-07-17
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

Julian quería tener el panel "como una app" en el celular, para vender y consultar desde el teléfono sin abrir el navegador. Ya existía el panel como **web React (Vite)** servida por Flask en `raloz-web.onrender.com`. Restricciones: negocio de una persona, presupuesto ajustado, sin equipo de desarrollo móvil, y necesidad de que sea rápido de tener.

## Decision

Convertir el panel en una **PWA (Progressive Web App) instalable**: `manifest.webmanifest` + service worker + íconos, de modo que se instale en la pantalla de inicio (modo `standalone`, sin barra del navegador) desde el propio navegador — **sin pasar por Play Store / App Store**.

## Options Considered

### Opción A: PWA instalable (elegida)
| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Baja (reusa el código web) |
| Costo | 0 (sin cuentas de tienda) |
| Tiempo | Horas |
| Familiaridad | Alta (mismo React) |

**Pros:** reutiliza el 100% del código; gratis; se actualiza sola con cada deploy; instala en Android e iPhone.
**Cons:** no aparece en las tiendas de apps; en iOS el push requiere iOS 16.4+.

### Opción B: App nativa con Capacitor (envolver la web)
**Pros:** sí sale en Play Store.
**Cons:** cuenta Google Play (25 USD única) + Apple (99 USD/año), build tooling y mantenimiento extra, para el mismo resultado práctico que la PWA.

### Opción C: App nativa desde cero (React Native)
**Pros:** máximo control nativo.
**Cons:** reescribir todo; meses de trabajo; sin sentido para este caso.

## Trade-off Analysis

El único beneficio real de B/C sobre A es **estar en las tiendas de apps**, que para un panel administrativo interno no aporta valor. La PWA da la experiencia de "app" (ícono, pantalla completa, offline básico) a costo y esfuerzo casi nulos, y deja la puerta abierta a envolver con Capacitor más adelante si algún día se necesita.

## Consequences

- ✅ **Más fácil:** instalación sin tiendas; una sola base de código; actualizaciones automáticas.
- ⚠️ **A vigilar:** el service worker **nunca** debe cachear `/api/*` (JWT/datos en vivo); iOS tiene límites de push; hay que subir `CACHE_VERSION` para forzar actualización de assets.
- 🔁 **A revisitar si:** se necesita presencia en Play Store o capacidades nativas (NFC, etc.) → Capacitor sobre la misma PWA.

## Action Items

1. [x] `manifest.webmanifest` (standalone, shortcuts) + íconos generados del logo.
2. [x] Service worker (network-first navegación, cache-first assets, nunca `/api`).
3. [x] Registrar el SW solo en producción; recarga al activar versión nueva.
4. [x] Flask sirve `sw.js`/manifest como archivos reales (catch-all con `os.path.isfile`).
