// frontend/src/infrastructure/api/client.ts
import axios from 'axios'
import { RequestError } from '@/application/errors/RequestError'
import type { AuthSessionPort } from '@/application/ports/AuthSessionPort'

const SKIP_REFRESH_URLS = ['/auth/refresh', '/auth/login', '/auth/me']

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

let authSession: AuthSessionPort | null = null

export function configureHttpClient(session: AuthSessionPort): void {
  authSession = session
}

export function getAccessToken(): string | null {
  return authSession?.getAccessToken() ?? null
}

client.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isLoggingOut = false
let refreshPromise: Promise<string> | null = null

function toRequestError(error: unknown): RequestError {
  if (error instanceof RequestError) return error
  if (!axios.isAxiosError(error)) return new RequestError(null, null)
  return new RequestError(error.response?.status ?? null, error.response?.data?.detail)
}

function redirectToLogin() {
  if (isLoggingOut) return
  isLoggingOut = true
  authSession?.clearAuth()
  authSession?.redirectToLogin()
}

async function refreshAccessToken(): Promise<string> {
  const res = await client.post<{ access_token: string }>('/auth/refresh')
  const token = res.data.access_token
  authSession?.setAuth(token, authSession.getUsername() ?? '')
  return token
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const status = err.response?.status
    const url: string = original?.url ?? ''

    if (isLoggingOut) return Promise.reject(toRequestError(err))

    const shouldSkip = SKIP_REFRESH_URLS.some((u) => url.includes(u))

    if (status === 401 && !original._retry && !shouldSkip) {
      original._retry = true

      try {
        if (refreshPromise === null) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
          })
        }
        const newToken = await refreshPromise
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch (refreshError) {
        redirectToLogin()
        return Promise.reject(toRequestError(refreshError))
      }
    }

    return Promise.reject(toRequestError(err))
  }
)

export default client
