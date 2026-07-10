// frontend/src/app/store/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  loginRequired: boolean
  username: string | null
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
      setAuth: (token, username) => set({ accessToken: token, username }),
      setLoginRequired: (v) => set({ loginRequired: v }),
      clearAuth: () => set({ accessToken: null, username: null, loginRequired: true }),
    }),
    {
      name: 'auth-storage',
      partialize: (s) => ({ accessToken: s.accessToken, username: s.username }),
    }
  )
)
