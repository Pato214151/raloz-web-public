# Architecture Decision Records (ADR)

Registro de las decisiones de arquitectura importantes de RALOZ, con su contexto,
las opciones que se consideraron y por qué se eligió una. Sirve para entender
*por qué* el sistema está armado así, sin tener que adivinar más adelante.

> Un ADR no se edita cuando la realidad cambia: se marca como `Superseded` y se
> escribe uno nuevo que lo reemplace.

| # | Decisión | Estado | Fecha |
|---|----------|--------|-------|
| [001](ADR-001-whatsapp-bot-en-backend.md) | Bot de WhatsApp dentro del backend (no servicio aparte) | Accepted | 2026-07-24 |
| [002](ADR-002-panel-pwa-instalable.md) | Panel como PWA instalable (no app nativa) | Accepted | 2026-07-17 |
| [003](ADR-003-nueva-venta-visual.md) | Nueva Venta visual `/vender` al lado del clásico | Accepted | 2026-07-20 |
| [004](ADR-004-fotos-producto-estaticas.md) | Fotos de producto empacadas como assets estáticos | Accepted | 2026-07-20 |
| [005](ADR-005-notificaciones-push.md) | Notificaciones de WhatsApp por Web Push a la PWA | Accepted | 2026-07-20 |
| [006](ADR-006-impresion-ticket.md) | Impresión del ticket client-side 76 mm desde el PC | Accepted | 2026-07-17 |

## Cómo agregar uno nuevo

1. Copia el formato de un ADR existente (Context · Decision · Options · Trade-off · Consequences · Action Items).
2. Numéralo consecutivo (`ADR-00N-titulo-corto.md`).
3. Agrégalo a esta tabla.
