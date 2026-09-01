// frontend/src/presentation/components/layout/ThemeToggle.tsx
import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/presentation/state/themeStore'

interface Props {
  collapsed?: boolean
}

export default function ThemeToggle({ collapsed = false }: Props) {
  const theme = useThemeStore((state) => state.theme)
  const toggleTheme = useThemeStore((state) => state.toggleTheme)
  const isDark = theme === 'dark'
  const actionLabel = isDark ? '라이트 모드로 전환' : '다크 모드로 전환'

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={actionLabel}
      title={actionLabel}
      onClick={toggleTheme}
      className={[
        'group flex h-9 items-center rounded-xl text-apple-light transition-colors',
        'hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/50',
        collapsed ? 'w-9 justify-center' : 'w-full justify-between gap-3 px-3',
      ].join(' ')}
    >
      <span className="flex min-w-0 items-center gap-2">
        {isDark ? <Moon size={15} /> : <Sun size={15} />}
        {!collapsed && <span className="truncate text-[12px] font-medium">{isDark ? '다크 모드' : '라이트 모드'}</span>}
      </span>
      {!collapsed && (
        <span
          aria-hidden="true"
          className={[
            'relative h-5 w-9 flex-shrink-0 rounded-full transition-colors',
            isDark ? 'bg-brand-600' : 'bg-apple-divider',
          ].join(' ')}
        >
          <span
            className={[
              'absolute left-0 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform',
              isDark ? 'translate-x-[18px]' : 'translate-x-0.5',
            ].join(' ')}
          />
        </span>
      )}
    </button>
  )
}
