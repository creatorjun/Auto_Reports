// frontend/src/infrastructure/api/client.ts
import axios, { type InternalAxiosRequestConfig } from 'axios'
import { RequestError } from '@/application/errors/RequestError'
import type { AuthSessionPort } from '@/application/ports/AuthSessionPort'
import type { TokenResponse } from '@/domain/Auth'

interface SessionRequestConfig extends InternalAxiosRequestConfig {
  _authGeneration?: number
  _retry?: boolean
}

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

let authSession: AuthSessionPort | null = null
let authGeneration = 0
let isLoggingOut = false
let refreshPromise: Promise<TokenResponse> | null = null
let logoutPromise: Promise<void> | null = null

export function configureHttpClient(session: AuthSessionPort): void {
  authSession = session
}

export function getAccessToken(): string | null {
  return authSession?.getAccessToken() ?? null
}

client.interceptors.request.use((config: SessionRequestConfig) => {
  config._authGeneration = authGeneration
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function toRequestError(error: unknown): Promise<RequestError> {
  if (error instanceof RequestError) return error
  if (!axios.isAxiosError(error)) return new RequestError(null, null)
  let data = error.response?.data
  if (data instanceof Blob && data.type.toLowerCase().includes('json')) {
    try {
      data = JSON.parse(await data.text())
    } catch {
      data = undefined
    }
  }
  return new RequestError(error.response?.status ?? null, data?.detail)
}

function sessionChanged(): RequestError {
  return new RequestError(401, '로그인 상태가 변경되었습니다.')
}

function beginAuthSessionChange(): number {
  authGeneration++
  isLoggingOut = false
  refreshPromise = null
  return authGeneration
}

function redirectToLogin() {
  if (isLoggingOut) return
  beginAuthSessionChange()
  isLoggingOut = true
  authSession?.clearAuth()
  authSession?.redirectToLogin()
}

export function refreshAuthSession(): Promise<TokenResponse> {
  if (logoutPromise) return Promise.reject(sessionChanged())
  if (refreshPromise) return refreshPromise
  const generation = authGeneration
  const pending = client.post<TokenResponse>('/auth/refresh')
    .then(({ data }) => {
      if (generation !== authGeneration) throw sessionChanged()
      authSession?.setAuth(data.access_token, data.display_name ?? data.username ?? authSession.getUsername() ?? '')
      return data
    })
    .finally(() => {
      if (refreshPromise === pending) refreshPromise = null
    })
  refreshPromise = pending
  return pending
}

export async function startAuthSession<T>(operation: () => Promise<T>): Promise<T> {
  const pendingRefresh = refreshPromise
  const generation = beginAuthSessionChange()
  if (pendingRefresh) await pendingRefresh.catch(() => undefined)
  if (logoutPromise) await logoutPromise.catch(() => undefined)
  if (generation !== authGeneration) throw sessionChanged()
  const result = await operation()
  if (generation !== authGeneration) throw sessionChanged()
  return result
}

export function endAuthSession(operation: () => Promise<void>): Promise<void> {
  if (logoutPromise) return logoutPromise
  const pendingRefresh = refreshPromise
  beginAuthSessionChange()
  authSession?.clearAuth()
  const pending = (async () => {
    if (pendingRefresh) await pendingRefresh.catch(() => undefined)
    await operation()
  })().finally(() => {
    if (logoutPromise === pending) logoutPromise = null
  })
  logoutPromise = pending
  return pending
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original: SessionRequestConfig | undefined = err.config
    const status = err.response?.status
    const url = original?.url ?? ''
    const isSessionEndpoint = url.includes('/auth/') && !url.startsWith('/auth/jira/privacy/')

    if (isLoggingOut || logoutPromise || (original && original._authGeneration !== authGeneration)) {
      throw await toRequestError(err)
    }

    if (status === 401 && original && !original._retry && !isSessionEndpoint) {
      original._retry = true
      const generation = authGeneration
      try {
        const result = await refreshAuthSession()
        if (generation !== authGeneration) throw sessionChanged()
        original.headers.Authorization = `Bearer ${result.access_token}`
        return client(original)
      } catch (refreshError) {
        if (generation === authGeneration) redirectToLogin()
        throw await toRequestError(refreshError)
      }
    }

    throw await toRequestError(err)
  }
)

export default client
