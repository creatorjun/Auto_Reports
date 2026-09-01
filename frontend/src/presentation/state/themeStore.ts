// frontend/src/presentation/state/themeStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark'

interface ThemeStore {
  theme: ThemeMode
  toggleTheme: () => void
}

export function applyTheme(theme: ThemeMode) {
  document.documentElement.dataset.theme = theme
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'light',
      toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
    }),
    {
      name: 'auto-reports-theme',
      partialize: (state) => ({ theme: state.theme }),
      merge: (persisted, current) => {
        const stored = persisted as Partial<ThemeStore> | undefined
        return { ...current, theme: stored?.theme === 'dark' ? 'dark' : 'light' }
      },
    },
  ),
)
