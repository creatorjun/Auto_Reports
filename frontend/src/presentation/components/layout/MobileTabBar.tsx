// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { NavLink } from 'react-router-dom'
import TriggerButton from '../common/TriggerButton'

const tabs = [
  {
    to: '/',
    label: '대시보드',
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
    label: '히스토리',
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
      <div className="flex flex-col items-center gap-1">
        <TriggerButton collapsed />
        <span className="text-[10px] font-medium text-apple-light">생성</span>
      </div>
    </nav>
  )
}
