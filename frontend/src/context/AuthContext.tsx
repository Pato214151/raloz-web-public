import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from 'react'
import api from '../services/api'
import type { Usuario } from '../types/api'

interface AuthResponse {
  access_token: string
  refresh_token: string
  usuario: Usuario
}

interface AuthContextType {
  usuario: Usuario | null
  loading: boolean
  login: (identificador: string, password: string) => Promise<Usuario>
  loginWithGoogle: (credential: string) => Promise<Usuario>
  logout: () => void
  isAdmin: () => boolean
  isVendedor: () => boolean
  isCajero: () => boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = (): void => {
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

  useEffect(() => {
    // Verificar sesión al cargar
    const token = localStorage.getItem('access_token')
    const savedUser = localStorage.getItem('usuario')

    if (token && savedUser) {
      try {
        setUsuario(JSON.parse(savedUser) as Usuario)
      } catch {
        logout()
      }
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = async (identificador: string, password: string): Promise<Usuario> => {
    const res = await api.post<AuthResponse>('/auth/login', {
      usuario: identificador,
      password,
    })
    const { access_token, refresh_token, usuario: user } = res.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('usuario', JSON.stringify(user))
    setUsuario(user)
    return user
  }

  const loginWithGoogle = async (credential: string): Promise<Usuario> => {
    const res = await api.post<AuthResponse>('/auth/google', { credential })
    const { access_token, refresh_token, usuario: user } = res.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('usuario', JSON.stringify(user))
    setUsuario(user)
    return user
  }

  const isAdmin = () => usuario?.rol === 'administrador'
  const isVendedor = () => usuario?.rol === 'vendedor'
  const isCajero = () => usuario?.rol === 'cajero'

  return (
    <AuthContext.Provider
      value={{
        usuario,
        loading,
        login,
        loginWithGoogle,
        logout,
        isAdmin,
        isVendedor,
        isCajero,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return context
}
