// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { useEffect, useId, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, List, Clock, ListChecks, Building2, HardDrive, ShieldCheck, ChevronUp, Newspaper, UserRound } from 'lucide-react'
import { canViewAuditLogs } from '@/domain/Auth'
import { useMe } from '@/presentation/hooks/useAuth'
import { FOCUS_MANAGEMENT_LABEL, FOCUS_MANAGEMENT_LINKS, isFocusManagementPath } from '@/presentation/config/focusManagement'

const tabs = [
  { to: '/',        label: '대시보드', icon: <LayoutDashboard size={20} /> },
  { to: '/issues',  label: '전체 이슈', icon: <List            size={20} /> },
  { to: '/sites',   label: '사이트',     icon: <Building2      size={20} /> },
  { to: '/sla-dashboard', label: '장기 이슈', icon: <Clock     size={20} /> },
  { to: '/storage', label: '보관함',     icon: <HardDrive      size={20} /> },
  { to: '/security-news', label: '보안 뉴스', icon: <Newspaper size={20} /> },
]

interface Props {
  onOpenAccount?: (trigger: HTMLButtonElement) => void
  accountExpanded?: boolean
}

export default function MobileTabBar({ onOpenAccount, accountExpanded = false }: Props) {
  const me = useMe()
  const { pathname } = useLocation()
  const [expanded, setExpanded] = useState(false)
  const menuId = useId()
  const menu = useRef<HTMLElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  useEffect(() => { setExpanded(false) }, [pathname])
  useEffect(() => { if (expanded) menu.current?.querySelector('a')?.focus() }, [expanded])
  const visibleTabs = !me.isError && canViewAuditLogs(me.data)
    ? [...tabs, { to: '/audit-logs', label: '감사로그', icon: <ShieldCheck size={20} /> }] : tabs

  return (
    <div className="xl:hidden" onKeyDown={(event) => {
      if (event.key === 'Escape' && expanded) {
        setExpanded(false)
        trigger.current?.focus()
      }
    }}>
      {expanded && <button type="button" aria-label="집중 관리 메뉴 닫기" onClick={() => setExpanded(false)} className="fixed inset-0 z-20 cursor-default bg-black/10" />}
      <nav
        aria-label="주 메뉴"
        className="fixed bottom-0 left-0 right-0 z-30 xl:hidden bg-apple-surface/90 backdrop-blur-xl border-t border-apple-divider/80 flex items-center justify-around overflow-x-auto px-1 h-20 safe-area-inset-bottom"
      >
        {visibleTabs.map(({ to, icon, label }) => (
          <div key={to} className="contents">
          <NavLink
            to={to}
            aria-label={label}
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
          {to === '/issues' && <button ref={trigger} type="button" aria-expanded={expanded} aria-controls={menuId} onClick={() => setExpanded((value) => !value)} className={`flex min-w-12 shrink-0 flex-col items-center gap-1 rounded-xl px-1.5 py-1 ${expanded || isFocusManagementPath(pathname) ? 'text-brand-600' : 'text-apple-light'}`}><ListChecks size={20} /><span className="flex items-center gap-1 text-control-label font-medium">{FOCUS_MANAGEMENT_LABEL}<ChevronUp size={12} className={expanded ? 'rotate-180' : ''} /></span></button>}
          </div>
        ))}
        {onOpenAccount && !me.isError && me.data?.login_required && <button type="button" aria-label="계정 메뉴" aria-expanded={accountExpanded} onClick={(event) => { setExpanded(false); onOpenAccount(event.currentTarget) }} className={`flex min-w-12 shrink-0 flex-col items-center gap-1 rounded-xl px-1.5 py-1 ${accountExpanded ? 'text-brand-600' : 'text-apple-light'}`}><UserRound size={20} aria-hidden="true" /><span className="text-control-label font-medium">계정</span></button>}
      </nav>
      <nav ref={menu} id={menuId} hidden={!expanded} aria-label={FOCUS_MANAGEMENT_LABEL} className="fixed bottom-24 left-3 right-3 z-30 rounded-2xl border border-apple-divider bg-apple-surface p-3 shadow-xl">
        <p className="px-3 pb-2 text-caption font-semibold text-apple-mid">{FOCUS_MANAGEMENT_LABEL}</p>
        {FOCUS_MANAGEMENT_LINKS.map(({ to, label }) => <NavLink key={to} to={to} onClick={() => setExpanded(false)} className={({ isActive }) => `nav-link px-3 py-3 text-label ${isActive ? 'nav-link-active' : ''}`}>{label}</NavLink>)}
      </nav>
    </div>
  )
}
