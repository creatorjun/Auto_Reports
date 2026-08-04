// frontend/src/infrastructure/api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/app/store/authStore'

const SKIP_REFRESH_URLS = ['/auth/refresh', '/auth/login', '/auth/me']

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let isLoggingOut = false
let refreshQueue: Array<() => void> = []

function flushQueue() {
  refreshQueue.forEach((cb) => cb())
  refreshQueue = []
}

function redirectToLogin() {
  if (isLoggingOut) return
  isLoggingOut = true
  flushQueue()
  useAuthStore.getState().clearAuth()
  window.location.href = '/login'
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const status = err.response?.status
    const url: string = original?.url ?? ''

    if (isLoggingOut) {
      return new Promise(() => {})
    }

    const shouldSkip = SKIP_REFRESH_URLS.some((u) => url.includes(u))

    if (status === 401 && !original._retry && !shouldSkip) {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push(() => {
            const token = useAuthStore.getState().accessToken
            original.headers.Authorization = `Bearer ${token}`
            resolve(client(original))
          })
        })
      }

      isRefreshing = true
      try {
        const res = await client.post<{ access_token: string }>('/auth/refresh')
        const newToken = res.data.access_token
        useAuthStore.getState().setAuth(newToken, useAuthStore.getState().username ?? '')
        flushQueue()
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch {
        redirectToLogin()
        return new Promise(() => {})
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(err)
  }
)

export default client
