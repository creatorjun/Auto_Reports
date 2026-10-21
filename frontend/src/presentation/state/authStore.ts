// frontend/src/presentation/state/authStore.ts
import { create } from 'zustand'

interface AuthState {
  accessToken: string | null
  loginRequired: boolean
  username: string | null
  sessionReady: boolean
  sessionVersion: number
  setAuth: (token: string, username: string) => void
  setLoginRequired: (v: boolean) => void
  clearAuth: () => void
}

try {
  globalThis.localStorage?.removeItem('auth-storage')
} catch {}

export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  loginRequired: true,
  username: null,
  sessionReady: false,
  sessionVersion: 0,
  setAuth: (token, username) => set({ accessToken: token, username, sessionReady: true }),
  setLoginRequired: (value) => set(value ? { loginRequired: value } : { loginRequired: value, sessionReady: true }),
  clearAuth: () => set((state) => ({ accessToken: null, username: null, loginRequired: true, sessionReady: true, sessionVersion: state.sessionVersion + 1 })),
}))
