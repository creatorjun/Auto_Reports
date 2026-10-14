// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ListChecks, Gauge, Building2, HardDrive, ShieldCheck, AlarmClock, RotateCcw } from 'lucide-react'
import { canViewAuditLogs } from '@/domain/Auth'
import { useMe } from '@/presentation/hooks/useAuth'

const tabs = [
  { to: '/',        label: '대시보드', icon: <LayoutDashboard size={20} /> },
  { to: '/redeployments', label: '재배포 이슈', icon: <RotateCcw size={20} /> },
  { to: '/sla-violations', label: 'SLA 위반', icon: <AlarmClock size={20} /> },
  { to: '/issues',  label: '이슈 관리', icon: <ListChecks size={20} /> },
  { to: '/sla-dashboard', label: '장기 이슈', icon: <Gauge size={20} /> },
  { to: '/sites',   label: '사이트',     icon: <Building2      size={20} /> },
  { to: '/storage', label: '보관함',     icon: <HardDrive      size={20} /> },
]

export default function MobileTabBar() {
  const me = useMe()
  const visibleTabs = !me.isError && canViewAuditLogs(me.data)
    ? [...tabs, { to: '/audit-logs', label: '감사로그', icon: <ShieldCheck size={20} /> }] : tabs

  return (
    <>
      <nav
        className="fixed bottom-0 left-0 right-0 z-20 xl:hidden bg-apple-surface/90 backdrop-blur-xl border-t border-apple-divider/80 flex items-center justify-around overflow-x-auto px-1 h-16 safe-area-inset-bottom"
      >
        {visibleTabs.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex min-w-12 shrink-0 flex-col items-center gap-1 px-1.5 py-1 rounded-xl transition-colors ${
                isActive ? 'text-brand-600' : 'text-apple-light'
              }`
            }
          >
            {icon}
            <span className="max-w-full truncate text-control-label font-medium">{label}</span>
          </NavLink>
        ))}

      </nav>
    </>
  )
}
