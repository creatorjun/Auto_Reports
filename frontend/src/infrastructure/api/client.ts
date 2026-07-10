// frontend/src/infrastructure/api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/app/store/authStore'

const client = axios.create({
  baseURL: '/api/v1',
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
let refreshQueue: Array<(token: string) => void> = []

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const status = err.response?.status

    if (status === 401 && !original._retry && original.url !== '/auth/refresh' && original.url !== '/auth/login') {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token) => {
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
        refreshQueue.forEach((cb) => cb(newToken))
        refreshQueue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch {
        refreshQueue = []
        useAuthStore.getState().clearAuth()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    console.error('API Error:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)

export default client
