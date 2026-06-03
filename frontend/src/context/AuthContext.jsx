import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Verificar sesión al cargar
    const token = localStorage.getItem('access_token')
    const savedUser = localStorage.getItem('usuario')

    if (token && savedUser) {
      try {
        setUsuario(JSON.parse(savedUser))
      } catch {
        logout()
      }
    }
    setLoading(false)
  }, [])

  const login = async (identificador, password) => {
    const res = await api.post('/auth/login', { usuario: identificador, password })
    const { access_token, refresh_token, usuario: user } = res.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('usuario', JSON.stringify(user))
    setUsuario(user)
    return user
  }

  const loginWithGoogle = async (credential) => {
    const res = await api.post('/auth/google', { credential })
    const { access_token, refresh_token, usuario: user } = res.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('usuario', JSON.stringify(user))
    setUsuario(user)
    return user
  }

  const logout = () => {
    // Revoca los tokens en el backend (best-effort; no bloquea el cierre).
    // Se envía mientras el access_token sigue en localStorage para que el
    // interceptor adjunte el header Authorization.
    const refresh_token = localStorage.getItem('refresh_token')
    if (localStorage.getItem('access_token')) {
      api.post('/auth/logout', { refresh_token }).catch(() => {})
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('usuario')
    setUsuario(null)
  }

  const isAdmin = () => usuario?.rol === 'administrador'
  const isVendedor = () => usuario?.rol === 'vendedor'
  const isCajero = () => usuario?.rol === 'cajero'

  return (
    <AuthContext.Provider value={{
      usuario, loading, login, loginWithGoogle, logout,
      isAdmin, isVendedor, isCajero,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return context
}
