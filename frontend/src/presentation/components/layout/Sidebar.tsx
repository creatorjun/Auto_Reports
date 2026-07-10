// frontend/src/presentation/components/layout/Sidebar.tsx
import { NavLink } from 'react-router-dom'
import TriggerButton from '../common/TriggerButton'
import { useAuthStore } from '@/app/store/authStore'
import { useLogout } from '@/infrastructure/hooks/useAuth'

const reportLinks = [
  {
    to: '/',
    label: '\ub300\uc2dc\ubcf4\ub4dc',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.9" />
        <rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.3" />
      </svg>
    )
  },
  {
    to: '/history',
    label: '\ubcf4\uace0\uc11c \ud788\uc2a4\ud1a0\ub9ac',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="2" rx="1" fill="currentColor" />
        <rect x="2" y="6" width="9" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="10" width="11" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="14" width="6" height="1.5" rx="0.75" fill="currentColor" opacity="0.4" />
      </svg>
    )
  },
  {
    to: '/storage',
    label: '\ud30c\uc77c \ubcf4\uad00\ud568',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="4" width="14" height="10" rx="1.5" fill="currentColor" opacity="0.15" stroke="currentColor" strokeWidth="1.2" />
        <path d="M1 7h14" stroke="currentColor" strokeWidth="1.2" />
        <rect x="4" y="1.5" width="3" height="3" rx="0.75" fill="currentColor" opacity="0.6" />
        <rect x="9" y="1.5" width="3" height="3" rx="0.75" fill="currentColor" opacity="0.6" />
        <rect x="4" y="9.5" width="8" height="1.5" rx="0.75" fill="currentColor" opacity="0.4" />
      </svg>
    )
  }
]

function CollapseIcon({ collapsed }: { collapsed: boolean }) {
  return collapsed ? (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M5 2H2.5A.5.5 0 0 0 2 2.5v9a.5.5 0 0 0 .5.5H5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M9.5 9.5L12 7l-2.5-2.5M12 7H5.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

interface Props {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

export default function Sidebar({ collapsed, setCollapsed }: Props) {
  const { loginRequired, username } = useAuthStore()
  const { mutate: logout, isPending: isLoggingOut } = useLogout()

  return (
    <aside
      className={[
        collapsed ? 'w-14 3xl:w-16' : 'w-56 xl:w-60 2xl:w-64 3xl:w-72',
        'bg-white border-r border-apple-divider/80',
        'flex flex-col py-5 3xl:py-7 px-2 3xl:px-3',
        'transition-all duration-250 ease-in-out flex-shrink-0',
      ].join(' ')}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center w-8 h-8 3xl:w-10 3xl:h-10
                   rounded-xl text-apple-light
                   hover:bg-apple-gray hover:text-apple-dark
                   transition-all duration-200 mb-2 self-end"
        title={collapsed ? '\uc0ac\uc774\ub4dc\ubc14 \ud3bc\uce58\uae30' : '\uc0ac\uc774\ub4dc\ubc14 \uc811\uae30'}
      >
        <CollapseIcon collapsed={collapsed} />
      </button>

      <div className="flex flex-col gap-0.5 flex-1">
        {reportLinks.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              ['nav-link',
               collapsed ? 'justify-center px-0' : '',
               isActive ? 'nav-link-active' : '',
               '3xl:text-sm 3xl:py-2.5',
              ].join(' ')
            }
          >
            <span className="flex-shrink-0">{icon}</span>
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </div>

      <div className={['mt-auto pt-4 border-t border-apple-divider/60 flex flex-col', collapsed ? 'items-center' : ''].join(' ')}>
        <TriggerButton collapsed={collapsed} />

        {loginRequired && (
          <>
            <div className="w-full border-t border-apple-divider/50 my-2" />

            {collapsed ? (
              <button
                onClick={() => logout()}
                disabled={isLoggingOut}
                title={username ? `${username} · LOGOUT` : 'LOGOUT'}
                className="flex items-center justify-center w-8 h-8 rounded-xl
                           text-apple-light hover:text-red-500 hover:bg-red-50
                           transition-colors disabled:opacity-40"
              >
                <LogoutIcon />
              </button>
            ) : (
              <button
                onClick={() => logout()}
                disabled={isLoggingOut}
                className="flex items-center gap-2 w-full px-3 py-2 rounded-xl
                           text-[12px] font-medium tracking-wide
                           text-apple-light hover:text-red-500 hover:bg-red-50
                           transition-colors disabled:opacity-40"
              >
                <span className="flex-shrink-0"><LogoutIcon /></span>
                <span className="truncate">LOGOUT</span>
              </button>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
