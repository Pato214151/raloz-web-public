# ADR-004: Fotos de producto empacadas como assets estáticos

**Status:** Accepted
**Date:** 2026-07-20
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

El Nueva Venta visual ([ADR-003](ADR-003-nueva-venta-visual.md)) necesita **una foto por prenda**. Ya existían ~53 fotos organizadas por colegio y prenda en `fotos-prendas/`. Restricción clave: el backend corre en **Render con disco efímero** — cualquier archivo subido en tiempo de ejecución se borra en el siguiente deploy/reinicio. El volumen es pequeño (una tienda con 3 colegios).

## Decision

**Optimizar y empacar** las fotos como **assets estáticos** dentro del frontend: una foto principal por prenda, cuadrada (~500px, fondo blanco, WebP), en `frontend/public/prendas/{colegio}/{slug}.webp`. La resolución producto→foto se hace con un helper (`src/data/prendasFotos.js`) que normaliza nombres a slug. Si no hay foto, el `<img>` cae a un placeholder con `onError`.

## Options Considered

### Opción A: Assets estáticos empacados (elegida)
| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Baja |
| Costo | 0 |
| Persistencia | Total (van en el build) |

**Pros:** cero costo e infraestructura; sobreviven a Render efímero; carga rápida (WebP ~500px, <1 MB total); sin backend nuevo.
**Cons:** cambiar una foto exige reemplazar el archivo y redeployar; no es autogestionable por el usuario desde el panel.

### Opción B: Subida + almacenamiento externo (Supabase Storage / Cloudinary)
**Pros:** el usuario gestiona fotos desde el panel; sin redeploy.
**Cons:** endpoint de subida + integración + posible costo; más piezas que mantener; sobredimensionado para el volumen actual.

### Opción C: Guardar las fotos en la base de datos (BLOB/base64)
**Pros:** persistente sin servicio extra.
**Cons:** infla la BD y las respuestas; malo para rendimiento y backups.

## Trade-off Analysis

El eje es **simplicidad/costo vs. autogestión**. Para 3 colegios que cambian poco, la autogestión (B) no justifica su complejidad ni costo. Empacar estático (A) resuelve hoy con cero costo y máxima simplicidad, y deja el camino claro a B el día que el catálogo crezca o el usuario quiera subir fotos solo.

## Consequences

- ✅ **Más fácil:** desplegar y servir fotos sin infraestructura; rendimiento óptimo.
- ⚠️ **A vigilar:** actualizar fotos = reemplazar archivo + redeploy; Adventista aún sin fotos (muestra placeholder); mantener el mapeo slug↔nombre si cambian nombres de productos.
- 🔁 **A revisitar si:** el catálogo crece o el usuario necesita gestionar fotos solo → migrar a almacenamiento externo (Opción B).

## Action Items

1. [x] Script PIL: 1 foto/prenda, cuadrada, WebP ~500px, a `public/prendas/`.
2. [x] `src/data/prendasFotos.js` con `fotoPrenda(colegio, producto)` (normaliza acentos y "Educación Física"→"ed-fisica").
3. [x] `<img>` con fallback a placeholder vía `onError`.
