import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import toast from 'react-hot-toast'
import { User, Lock } from 'lucide-react'

export default function Login() {
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleReady, setGoogleReady] = useState(false)
  const { login, loginWithGoogle } = useAuth()
  const navigate = useNavigate()

  // Cargar Google Sign-In SDK
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return

    // Evitar cargar el script dos veces
    if (document.querySelector('script[src*="accounts.google.com/gsi/client"]')) {
      setGoogleReady(!!window.google)
      return
    }

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => setGoogleReady(true)
    document.body.appendChild(script)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!identificador || !password) {
      toast.error('Ingresa usuario y contraseña')
      return
    }

    setLoading(true)
    try {
      await login(identificador, password)
      toast.success('Bienvenido a RALOZ')
      navigate('/')
    } catch (err) {
      const msg = err.response?.data?.error || 'Error al iniciar sesión'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    if (!googleReady || !window.google) {
      toast.error('Google Sign-In no disponible')
      return
    }

    try {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            setLoading(true)
            await loginWithGoogle(response.credential)
            toast.success('Bienvenido a RALOZ')
            navigate('/')
          } catch (err) {
            const msg = err.response?.data?.error || 'Error con Google'
            toast.error(msg)
          } finally {
            setLoading(false)
          }
        },
      })
      window.google.accounts.id.prompt()
    } catch (err) {
      toast.error('Error al iniciar con Google')
    }
  }

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-raloz-950 via-raloz-900 to-raloz-800 p-4">
      <div className="w-full max-w-sm">

        {/* Marca */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-20 h-20 rounded-2xl bg-white shadow-lg flex items-center justify-center mb-3 overflow-hidden ring-4 ring-white/10">
            <img src="/apple-touch-icon.png" alt="RALOZ" className="w-16 h-16 object-contain" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">RALOZ COL SAS</h1>
          <p className="text-amber-300/80 text-sm font-medium">Uniformes Escolares · Panel</p>
        </div>

        {/* Tarjeta */}
        <div className="bg-white rounded-2xl shadow-2xl p-6 sm:p-8">
          <h2 className="text-lg font-bold text-gray-800">Iniciar sesión</h2>
          <p className="text-sm text-gray-400 mb-6">Ingresa a tu panel</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Usuario o Email</label>
              <div className="relative">
                <User size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={identificador}
                  onChange={(e) => setIdentificador(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-raloz-500 focus:border-transparent"
                  placeholder="admin o tu@email.com"
                  autoComplete="username"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Contraseña</label>
              <div className="relative">
                <Lock size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-raloz-500 focus:border-transparent"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-raloz-600 hover:bg-raloz-700 disabled:opacity-60 text-white font-bold text-base transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                  Ingresando…
                </span>
              ) : 'Ingresar'}
            </button>
          </form>

          {/* Google Login - solo si hay client_id configurado */}
          {googleClientId && (
            <>
              <div className="flex items-center my-6">
                <div className="flex-1 border-t border-gray-200"></div>
                <span className="px-3 text-xs text-gray-400">o</span>
                <div className="flex-1 border-t border-gray-200"></div>
              </div>

              <button
                onClick={handleGoogleLogin}
                disabled={loading || !googleReady}
                className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <span className="font-medium text-gray-700 text-sm">Continuar con Google</span>
              </button>
            </>
          )}
        </div>

        <p className="text-center text-xs text-white/40 mt-6">RALOZ COL SAS · v1.0.0-beta</p>
      </div>
    </div>
  )
}
