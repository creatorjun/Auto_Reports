// frontend/src/presentation/state/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  loginRequired: boolean
  username: string | null
  sessionReady: boolean
  setAuth: (token: string, username: string) => void
  setLoginRequired: (v: boolean) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      loginRequired: true,
      username: null,
      sessionReady: false,
      setAuth: (token, username) => set({ accessToken: token, username, sessionReady: true }),
      setLoginRequired: (v) => set(v ? { loginRequired: v } : { loginRequired: v, sessionReady: true }),
      clearAuth: () => set({ accessToken: null, username: null, loginRequired: true, sessionReady: true }),
    }),
    {
      name: 'auth-storage',
      partialize: (s) => ({ username: s.username }),
    }
  )
)
