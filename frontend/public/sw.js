/* Service Worker del Panel RALOZ (PWA)
 * Estrategia:
 *  - /api/*            -> SOLO red (nunca se cachea: datos con sesión/JWT y en vivo)
 *  - navegaciones HTML -> red primero, con la última página cacheada como respaldo offline
 *  - assets estáticos  -> cache primero (Vite les pone hash en el nombre, así que es seguro)
 * Sube CACHE_VERSION para forzar que todos los clientes bajen los archivos nuevos.
 */
const CACHE_VERSION = 'raloz-panel-v2';
const APP_SHELL = '/';

// ── Notificaciones push (nuevo mensaje de WhatsApp, etc.) ──────────
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }
  const title = data.title || 'RALOZ';
  const options = {
    body: data.body || '',
    icon: '/pwa-192.png',
    badge: '/pwa-192.png',
    tag: data.tag || 'raloz',
    renotify: true,
    data: { url: data.url || '/whatsapp' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/whatsapp';
  event.waitUntil(
    (async () => {
      const clientsArr = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const c of clientsArr) {
        if ('focus' in c) { c.navigate(url); return c.focus(); }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })()
  );
});

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll([APP_SHELL]).catch(() => {}))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  // Solo gestionamos peticiones del mismo origen
  if (url.origin !== self.location.origin) return;

  // Nunca tocar la API (auth/JWT, datos en vivo)
  if (url.pathname.startsWith('/api/')) return;

  // Navegaciones (rutas de la SPA): red primero, respaldo a la caché
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(APP_SHELL, copy)).catch(() => {});
          return res;
        })
        .catch(async () => (await caches.match(request)) || (await caches.match(APP_SHELL)))
    );
    return;
  }

  // Assets estáticos: caché primero, y en segundo plano refresca
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(request, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
