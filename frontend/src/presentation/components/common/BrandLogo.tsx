// frontend/src/presentation/components/common/BrandLogo.tsx
import lightLogo from '@/assets/seculayer-wordmark-light.png'
import darkLogo from '@/assets/seculayer-wordmark-dark.png'
import { useThemeStore } from '@/presentation/state/themeStore'

export default function BrandLogo({ className = '' }: { className?: string }) {
  const theme = useThemeStore((state) => state.theme)

  return (
    <img
      src={theme === 'dark' ? darkLogo : lightLogo}
      alt="SecuLayer"
      className={`block h-auto object-contain ${className}`}
    />
  )
}
