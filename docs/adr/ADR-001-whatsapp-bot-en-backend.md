# ADR-001: Ejecutar el bot de WhatsApp dentro del backend (no como servicio aparte)

**Status:** Accepted
**Date:** 2026-07-24
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

RALOZ opera con la **WhatsApp Cloud API de Meta**: los mensajes de los clientes NO llegan a una app de WhatsApp en el celular, sino que Meta hace un **webhook** a un servidor. Hasta ahora ese webhook lo atendía un **segundo servicio en Render** (`raloz-bot`), separado del backend/panel (`raloz-web`).

Fuerzas en juego:
- **Costo:** Render cobra ~**7 USD/mes por servicio**. El plan gratuito da ~750 horas/mes por cuenta; con dos servicios "siempre despiertos" (mantenidos por UptimeRobot) se agota y **suspende el servicio**. Eso dejó el bot caído hasta el siguiente ciclo de facturación. Para el negocio, cada dólar cuenta.
- **Disponibilidad:** el webhook de Meta debe responder siempre; un servicio dormido tarda ~1 min en despertar (retrasa la 1ª respuesta).
- **Acoplamiento:** el bot ya dependía del backend (catálogo, precios, bandeja de WhatsApp) vía HTTP.
- **Restricción técnica:** el backend corre con **2 workers de gunicorn**; el bot guardaba el estado de cada conversación **en memoria**, lo que se pierde entre workers.

## Decision

**Mover el bot al backend `raloz-web`** (un solo servicio pagado) exponiendo el webhook en `POST /api/whatsapp/webhook`, y **persistir el estado de conversación en la base de datos** en vez de memoria.

## Options Considered

### Opción A: Mantener el bot como servicio Render separado (pagar el 2º servicio)
| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Baja (ya existía) |
| Costo | **+7 USD/mes** permanente |
| Escalabilidad | Buena (aislado) |
| Familiaridad | Alta |

**Pros:** cero trabajo; aislamiento de fallos; el bot puede escalar aparte.
**Cons:** costo recurrente que el negocio no quiere/puede asumir; duplica infraestructura para tráfico bajo.

### Opción B: Integrar el bot en el backend (elegida)
| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Media (migración + estado en BD) |
| Costo | **0 extra** (usa el servicio ya pagado) |
| Escalabilidad | Suficiente para el tráfico actual (tienda pequeña) |
| Familiaridad | Alta (mismo stack Flask) |

**Pros:** sin costo adicional nunca; un solo servicio que mantener; el bot responde siempre rápido (sin cold start); reutiliza la sesión de BD y la lógica de la bandeja en proceso.
**Cons:** un fallo del backend tumba también el bot; el estado debía volverse persistente (2 workers); `responses.py` hace auto-HTTP para catálogo/precios (aceptable con respaldo estático).

### Opción C: Dejar el bot en el plan gratis "durmiendo" (sin keep-alive)
| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Muy baja |
| Costo | 0 |
| Escalabilidad | Pobre |
| Familiaridad | Alta |

**Pros:** cero costo y cero código.
**Cons:** la 1ª respuesta tras inactividad tarda ~1 min (mala experiencia del cliente); **no resolvía el mes en curso** (el servicio gratis ya estaba suspendido por límite de horas).

## Trade-off Analysis

El eje central es **costo vs. aislamiento**. La Opción A compra aislamiento a cambio de un costo recurrente que el negocio quiere evitar. La Opción C es gratis pero degrada la experiencia y no desbloqueaba el mes en curso. La Opción B cuesta un esfuerzo de migración **una sola vez** y elimina el costo **para siempre**, a cambio de acoplar bot y backend (aceptable: si el backend cae, el panel también, así que ya son un destino compartido).

El riesgo técnico real de B era el **estado en memoria con 2 workers**; se mitigó persistiéndolo en la BD (`WaConversacion.bot_estado/bot_datos`). El auto-HTTP de `responses.py` se aceptó porque el tráfico es bajo y ya degrada con gracia a datos estáticos; la parte más frecuente (registrar en la bandeja) se hace **en proceso** para evitar auto-llamadas.

## Consequences

- ✅ **Más fácil:** un solo servicio y un solo despliegue; sin costo del 2º servicio; el bot responde sin cold start.
- ⚠️ **Más difícil / a vigilar:** bot y backend comparten destino (un fallo afecta a ambos); el estado del bot ahora pega a la BD en cada mensaje (costo mínimo hoy, revisar si el tráfico crece); el auto-HTTP podría estresar los 2 workers en picos altos.
- 🔁 **A revisitar si:** el volumen de WhatsApp crece mucho → considerar reintroducir un servicio dedicado, o reemplazar el auto-HTTP por acceso directo a la BD dentro de `responses.py`.

## Action Items

1. [x] Portar `bot_meta.py` a un blueprint en `app/api/whatsapp_webhook.py` (`/api/whatsapp/webhook`).
2. [x] Mover `responses.py` y `state.py` a `app/bot/`; estado en BD (migración 0025).
3. [x] Extraer `registrar_mensaje_inbox()` para loguear en proceso (con push).
4. [x] Configurar env en `raloz-web` (`VERIFY_TOKEN`, `APP_SECRET`, …) y apuntar el webhook de Meta a la URL nueva. **Verificado en producción el 2026-07-24.**
5. [ ] Borrar el servicio `raloz-bot` en Render y su monitor en UptimeRobot.
6. [ ] Probar flujos multipaso (garantía con foto, citas) para confirmar la persistencia de estado.
