/* Service Worker del Panel RALOZ (PWA)
 * Estrategia:
 *  - /api/*            -> SOLO red (nunca se cachea: datos con sesión/JWT y en vivo)
 *  - navegaciones HTML -> red primero, con la última página cacheada como respaldo offline
 *  - assets estáticos  -> cache primero (Vite les pone hash en el nombre, así que es seguro)
 * Sube CACHE_VERSION para forzar que todos los clientes bajen los archivos nuevos.
 */
const CACHE_VERSION = 'raloz-panel-v1';
const APP_SHELL = '/';

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
