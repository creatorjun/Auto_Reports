// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { NavLink } from 'react-router-dom'
import { useTrigger } from '@/infrastructure/hooks/useTrigger'
import { useUiStore } from '@/app/store/uiStore'

const tabs = [
  {
    to: '/',
    label: '\ub300\uc2dc\ubcf4\ub4dc',
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.9" />
        <rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.3" />
      </svg>
    )
  },
  {
    to: '/history',
    label: '\ud788\uc2a4\ud1a0\ub9ac',
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="2" rx="1" fill="currentColor" />
        <rect x="2" y="6" width="9" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="10" width="11" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="14" width="6" height="1.5" rx="0.75" fill="currentColor" opacity="0.4" />
      </svg>
    )
  }
]

export default function MobileTabBar() {
  const { mutate } = useTrigger()
  const { isTriggerLoading } = useUiStore()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 bg-white/90 backdrop-blur-xl
                    border-t border-apple-divider/80 flex items-center justify-around
                    px-4 h-16 safe-area-inset-bottom">
      {tabs.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex flex-col items-center gap-1 px-4 py-1 rounded-xl transition-colors ${
              isActive ? 'text-brand-600' : 'text-apple-light'
            }`
          }
        >
          {icon}
          <span className="text-[10px] font-medium">{label}</span>
        </NavLink>
      ))}

      <button
        onClick={() => mutate()}
        disabled={isTriggerLoading}
        title="\ubcf4\uace0\uc11c \uc0dd\uc131"
        className="flex flex-col items-center gap-1 px-4 py-1 rounded-xl
                   text-brand-600 transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed
                   active:scale-95"
      >
        {isTriggerLoading ? (
          <span className="w-5 h-5 flex items-center justify-center">
            <span className="w-4 h-4 border-2 border-brand-600/30 border-t-brand-600 rounded-full animate-spin" />
          </span>
        ) : (
          <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
            <rect x="1" y="1" width="14" height="14" rx="3.5" fill="currentColor" opacity="0.15" />
            <path d="M8 4v8M4 8h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        )}
        <span className="text-[10px] font-medium">
          {isTriggerLoading ? '\uc0dd\uc131 \uc911' : '\uc0dd\uc131'}
        </span>
      </button>
    </nav>
  )
}
