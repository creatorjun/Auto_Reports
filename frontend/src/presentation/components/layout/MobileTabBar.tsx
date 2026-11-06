// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { useEffect, useId, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, List, Clock, ListChecks, Building2, HardDrive, ShieldCheck, ShieldAlert, ChevronUp, Newspaper, UserRound, CalendarRange, Users } from 'lucide-react'
import { canViewAuditLogs, canViewSiteManagement } from '@/domain/Auth'
import { useMe } from '@/presentation/hooks/useAuth'
import { useAuthStore } from '@/presentation/state/authStore'
import { FOCUS_MANAGEMENT_LABEL, FOCUS_MANAGEMENT_LINKS } from '@/presentation/config/focusManagement'
import { CVE_VULNERABILITIES_LABEL, CVE_VULNERABILITY_LINKS } from '@/presentation/config/cveVulnerabilities'
import { ANNUAL_REPORT_YEARS } from '@/presentation/config/annualReports'

const groups = [
  { id: 'focus', label: FOCUS_MANAGEMENT_LABEL, icon: <ListChecks size={20} />, children: FOCUS_MANAGEMENT_LINKS },
  { id: 'cve', label: CVE_VULNERABILITIES_LABEL, icon: <ShieldAlert size={20} />, children: CVE_VULNERABILITY_LINKS },
  { id: 'annual', label: '연간 보고서', icon: <CalendarRange size={20} />, children: ANNUAL_REPORT_YEARS.map((year) => ({ to: `/reports/annual/${year}`, label: `${year}`, ariaLabel: `${year} 연간 보고서` })) },
]

const tabs = [
  { to: '/',        label: '대시보드', icon: <LayoutDashboard size={20} /> },
  { to: '/issues',  label: '전체 이슈', icon: <List            size={20} /> },
  { to: '/partners', label: '파트너 관리', icon: <Users       size={20} /> },
  { to: '/sla-dashboard', label: '장기 이슈', icon: <Clock     size={20} /> },
  { to: '/security-news', label: '보안 뉴스', icon: <Newspaper size={20} /> },
  { to: '/storage', label: '파일 보관함', icon: <HardDrive     size={20} /> },
  { to: '/sites',   label: '사이트 관리', icon: <Building2     size={20} /> },
]

interface Props {
  onOpenAccount?: (trigger: HTMLButtonElement) => void
  accountExpanded?: boolean
}

export default function MobileTabBar({ onOpenAccount, accountExpanded = false }: Props) {
  const me = useMe()
  const { accessToken } = useAuthStore()
  const siteManagementVisible = !!accessToken && !me.isPending && !me.isError && canViewSiteManagement(me.data)
  const { pathname } = useLocation()
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)
  const menuId = useId()
  const menu = useRef<HTMLElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  useEffect(() => { setExpandedGroup(null) }, [pathname])
  useEffect(() => { if (expandedGroup) menu.current?.querySelector('a')?.focus() }, [expandedGroup])
  const reportTabs = tabs.filter((item) => item.to !== '/sites' || siteManagementVisible)
  const visibleTabs = !me.isError && canViewAuditLogs(me.data)
    ? [...reportTabs, { to: '/audit-logs', label: '감사로그', icon: <ShieldCheck size={20} /> }] : reportTabs

  return (
    <div className="xl:hidden" onKeyDown={(event) => {
      if (event.key === 'Escape' && expandedGroup) {
        setExpandedGroup(null)
        trigger.current?.focus()
      }
    }}>
      {expandedGroup && <button type="button" aria-label={`${groups.find((group) => group.id === expandedGroup)?.label} 메뉴 닫기`} onClick={() => setExpandedGroup(null)} className="fixed inset-0 z-20 cursor-default bg-black/10" />}
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
          {to === '/issues' && groups.map((group) => {
            const expanded = expandedGroup === group.id
            const active = group.children.some(({ to }) => pathname === to || pathname.startsWith(`${to}/`))
            return <button key={group.id} ref={expanded ? trigger : undefined} type="button" aria-label={group.label} aria-expanded={expanded} aria-controls={`${menuId}-${group.id}`} onClick={() => setExpandedGroup(expanded ? null : group.id)} className={`flex min-w-12 shrink-0 flex-col items-center gap-1 rounded-xl px-1.5 py-1 ${expanded || active ? 'text-brand-600' : 'text-apple-light'}`}>{group.icon}<span className="flex items-center gap-1 text-control-label font-medium">{group.label}<ChevronUp size={12} className={expanded ? 'rotate-180' : ''} /></span></button>
          })}
          </div>
        ))}
        {onOpenAccount && !me.isError && me.data?.login_required && <button type="button" aria-label="계정 메뉴" aria-expanded={accountExpanded} onClick={(event) => { setExpandedGroup(null); onOpenAccount(event.currentTarget) }} className={`flex min-w-12 shrink-0 flex-col items-center gap-1 rounded-xl px-1.5 py-1 ${accountExpanded ? 'text-brand-600' : 'text-apple-light'}`}><UserRound size={20} aria-hidden="true" /><span className="text-control-label font-medium">계정</span></button>}
      </nav>
      {groups.map((group) => <nav key={group.id} ref={expandedGroup === group.id ? menu : undefined} id={`${menuId}-${group.id}`} hidden={expandedGroup !== group.id} aria-label={group.label} className="fixed bottom-24 left-3 right-3 z-30 rounded-2xl border border-apple-divider bg-apple-surface p-3 shadow-xl">
        <p className="px-3 pb-2 text-caption font-semibold text-apple-mid">{group.label}</p>
        {group.children.map((child) => <NavLink key={child.to} to={child.to} aria-label={'ariaLabel' in child ? child.ariaLabel : child.label} onClick={() => setExpandedGroup(null)} className={({ isActive }) => `nav-link px-3 py-3 text-label ${isActive ? 'nav-link-active' : ''}`}>{child.label}</NavLink>)}
      </nav>)}
    </div>
  )
}
