// frontend/src/presentation/components/layout/ThemeController.tsx
import { useLayoutEffect } from 'react'
import { applyTheme, useThemeStore } from '@/presentation/state/themeStore'

export default function ThemeController() {
  const theme = useThemeStore((state) => state.theme)

  useLayoutEffect(() => {
    applyTheme(theme)
  }, [theme])

  return null
}
