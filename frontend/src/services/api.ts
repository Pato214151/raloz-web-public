/**
 * Cliente HTTP (axios) hacia la API. Agrega el token JWT a cada petición y,
 * si una respuesta da 401, intenta refrescar el token una vez; si falla,
 * cierra la sesión y manda al login.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

const API_URL: string = import.meta.env.VITE_API_URL || '/api'

// El interceptor marca la request reintentada tras refrescar el token.
interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor: agregar token JWT a cada request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor: manejar errores y refresh token
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequest | undefined
    if (!originalRequest) return Promise.reject(error)

    // No redirigir si es la propia llamada de login/refresh
    if (
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/google') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const res = await axios.post<{ access_token: string }>(
            `${API_URL}/auth/refresh`,
            {},
            { headers: { Authorization: `Bearer ${refreshToken}` } },
          )
          const { access_token } = res.data
          localStorage.setItem('access_token', access_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh falló, cerrar sesión
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('usuario')
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  },
)

export default api
