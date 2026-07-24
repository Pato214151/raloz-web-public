# ADR-005: Notificaciones de WhatsApp por Web Push a la PWA

**Status:** Accepted
**Date:** 2026-07-20
**Deciders:** Julian (dueño/operación) · implementación asistida

## Context

Con la **WhatsApp Cloud API de Meta**, los mensajes de los clientes **no llegan a una app de WhatsApp** en el celular; solo entran a la bandeja del panel. Resultado: si Julian no está mirando el panel, no se entera de que un cliente escribió — se pierden ventas. Julian usa **Android** y ya tiene el panel instalado como PWA ([ADR-002](ADR-002-panel-pwa-instalable.md)).

## Decision

Enviar **notificaciones Web Push** a la PWA: cuando llega un mensaje entrante, el celular recibe un aviso "💬 [cliente]: [texto]" aunque la app esté cerrada. Implementado con **VAPID + pywebpush** en el backend, suscripción desde el frontend (botón 🔔 en la bandeja) y manejo `push`/`notificationclick` en el service worker. El disparo se hace **en proceso** desde el registro del mensaje entrante (`registrar_mensaje_inbox`), best-effort.

## Options Considered

### Opción A: Web Push a la PWA (elegida)
**Pros:** no requiere apps extra (usa la PWA ya instalada); integrado; gratis. En Android funciona muy bien.
**Cons:** en iPhone solo funciona con iOS 16.4+ y app instalada; requiere gestionar llaves VAPID y suscripciones.

### Opción B: Notificación por Telegram
**Pros:** muy confiable e instantáneo en cualquier celular; poco código (un POST a la API de Telegram).
**Cons:** exige instalar Telegram y una configuración inicial de bot; es "otra app" fuera del panel.

### Opción C: Notificación por email
**Pros:** trivial (ya hay Brevo).
**Cons:** lento y fácil de ignorar; no sirve para "enterarme al instante".

## Trade-off Analysis

Como el usuario es Android y ya tiene la PWA instalada, Web Push (A) da la experiencia más nativa sin pedirle instalar nada más. Telegram (B) es un plan B sólido si algún día se necesita algo independiente del panel o multi-dispositivo sin fricción. Email (C) queda descartado para avisos en tiempo real.

## Consequences

- ✅ **Más fácil:** avisos instantáneos en el mismo dispositivo del panel, sin apps extra.
- ⚠️ **A vigilar:** requiere `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_SUBJECT` en Render (sin ellas queda inerte, no rompe); avisa por **cada** mensaje entrante (posible ruido — se puede limitar a modo humano o no-leídos); iOS necesita 16.4+.
- 🔁 **A revisitar si:** hay demasiadas notificaciones → filtrar; si se quiere multi-dispositivo simple → añadir Telegram.

## Action Items

1. [x] Modelo `PushSubscription` (migración 0024) + `app/api/push.py` (public-key/subscribe/unsubscribe/test) con `pywebpush`.
2. [x] Disparo desde `registrar_mensaje_inbox` cuando `direccion == 'in'` (best-effort).
3. [x] Frontend `src/services/push.js` + botón 🔔 en la bandeja; SW maneja `push`/`notificationclick`.
4. [x] Llaves VAPID configuradas en Render.
