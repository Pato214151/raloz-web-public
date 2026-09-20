/**
 * Punto de entrada del panel: router + sesión + <App />, y registra el
 * service worker (PWA) solo en producción.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import App from './App'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)

// PWA: registrar el service worker solo en producción (en dev interfiere con Vite/HMR)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      // Si aparece una versión nueva, recargar cuando quede activa
      reg.addEventListener('updatefound', () => {
        const nuevo = reg.installing
        if (!nuevo) return
        nuevo.addEventListener('statechange', () => {
          if (nuevo.state === 'activated' && navigator.serviceWorker.controller) {
            window.location.reload()
          }
        })
      })
    }).catch(() => { /* sin PWA si falla el registro; la app sigue funcionando */ })
  })
}
