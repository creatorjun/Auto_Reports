// frontend/src/presentation/components/layout/Sidebar.tsx
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Gauge, History, Building2, HardDrive, Users, ChevronLeft, ChevronRight, LogOut } from 'lucide-react'
import TriggerButton from '../common/TriggerButton'
import { useAuthStore } from '@/presentation/state/authStore'
import { useLogout } from '@/presentation/hooks/useAuth'

const reportLinks = [
  { to: '/',         label: '대시보드',      icon: <LayoutDashboard size={16} /> },
  { to: '/sla-dashboard', label: 'SLA 대시보드', icon: <Gauge size={16} /> },
  { to: '/history',  label: '보고서 히스토리', icon: <History         size={16} /> },
  { to: '/partners', label: '파트너 관리',    icon: <Users           size={16} /> },
  { to: '/sites',    label: '사이트 관리',    icon: <Building2       size={16} /> },
  { to: '/storage',  label: '파일 보관함',    icon: <HardDrive       size={16} /> },
]

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
        title={collapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
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
                <LogOut size={14} />
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
                <span className="flex-shrink-0"><LogOut size={14} /></span>
                <span className="truncate">LOGOUT</span>
              </button>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
