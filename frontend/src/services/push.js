// Activa las notificaciones push del panel (Web Push) para este dispositivo.
import api from './api'

const soportado = () =>
  'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window

// base64url → Uint8Array (para applicationServerKey)
function urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

export function estadoNotificaciones() {
  if (!soportado()) return 'no-soportado'
  return Notification.permission // 'default' | 'granted' | 'denied'
}

/**
 * Pide permiso, se suscribe y registra la suscripción en el backend.
 * Devuelve { ok, motivo }.
 */
export async function activarNotificaciones() {
  if (!soportado()) return { ok: false, motivo: 'Este navegador no soporta notificaciones.' }

  const permiso = await Notification.requestPermission()
  if (permiso !== 'granted') return { ok: false, motivo: 'Permiso de notificaciones denegado.' }

  const reg = await navigator.serviceWorker.ready

  // Llave pública del servidor
  let publicKey
  try {
    const res = await api.get('/push/public-key')
    publicKey = res.data?.public_key
  } catch {
    return { ok: false, motivo: 'No se pudo obtener la configuración del servidor.' }
  }
  if (!publicKey) return { ok: false, motivo: 'El servidor no tiene las notificaciones configuradas.' }

  // Suscribir (reusa la existente si ya hay)
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlB64ToUint8Array(publicKey),
    })
  }

  await api.post('/push/subscribe', sub.toJSON())
  return { ok: true }
}
