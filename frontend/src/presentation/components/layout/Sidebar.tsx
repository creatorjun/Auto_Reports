// frontend/src/presentation/components/layout/Sidebar.tsx
import { useId, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, List, Clock, ListChecks, Building2, HardDrive, Users, ChevronDown, ChevronLeft, ChevronRight, LogOut, CalendarRange, ShieldCheck } from 'lucide-react'
import { useAuthStore } from '@/presentation/state/authStore'
import { useLogout, useMe } from '@/presentation/hooks/useAuth'
import { canViewAuditLogs } from '@/domain/Auth'
import ThemeToggle from './ThemeToggle'
import { ANNUAL_REPORT_YEARS } from '@/presentation/config/annualReports'
import { FOCUS_MANAGEMENT_LABEL, FOCUS_MANAGEMENT_LINKS } from '@/presentation/config/focusManagement'

const annualReportLinks = ANNUAL_REPORT_YEARS.map((year) => ({
  to: `/reports/annual/${year}`,
  label: `${year}`,
  ariaLabel: `${year} 연간 보고서`,
}))

const reportLinks = [
  { to: '/',         label: '대시보드',      icon: <LayoutDashboard size={16} /> },
  { to: '/issues',   label: '전체 이슈',     icon: <List            size={16} /> },
  { id: 'focus', label: FOCUS_MANAGEMENT_LABEL, icon: <ListChecks size={16} />, children: FOCUS_MANAGEMENT_LINKS },
  { id: 'annual', label: '연간 보고서', icon: <CalendarRange size={16} />, children: annualReportLinks },
  { to: '/partners', label: '파트너 관리',    icon: <Users           size={16} /> },
  { to: '/sites',    label: '사이트 관리',    icon: <Building2       size={16} /> },
  { to: '/sla-dashboard', label: '장기 이슈', icon: <Clock          size={16} /> },
  { to: '/storage',  label: '파일 보관함',    icon: <HardDrive       size={16} /> },
]

interface Props {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

export default function Sidebar({ collapsed, setCollapsed }: Props) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [hoveredGroup, setHoveredGroup] = useState<string | null>(null)
  const sidebarCollapsed = collapsed && hoveredGroup === null
  const submenuId = useId()
  const { pathname } = useLocation()
  const setGroupExpanded = (id: string, expanded: boolean) => setExpandedGroups((current) => {
    const next = new Set(current)
    if (expanded) next.add(id)
    else next.delete(id)
    return next
  })
  const closeGroup = (id: string) => {
    setGroupExpanded(id, false)
    setHoveredGroup((current) => current === id ? null : current)
  }
  const { loginRequired, username } = useAuthStore()
  const { mutate: logout, isPending: isLoggingOut } = useLogout()
  const me = useMe()

  return (
    <aside
      className={[
        sidebarCollapsed ? 'w-14 3xl:w-16' : 'w-56 xl:w-60 2xl:w-64 3xl:w-72',
        'bg-apple-surface border-r border-apple-divider/80',
        'flex flex-col whitespace-nowrap py-5 3xl:py-7 px-2 3xl:px-3',
        'transition-all duration-250 ease-in-out flex-shrink-0',
      ].join(' ')}
    >
      <button
        onClick={() => {
          setExpandedGroups(new Set())
          setHoveredGroup(null)
          setCollapsed(!sidebarCollapsed)
        }}
        className="flex items-center justify-center w-8 h-8 3xl:w-10 3xl:h-10 rounded-xl text-apple-light hover:bg-apple-gray hover:text-apple-dark transition-all duration-200 mb-2 self-end"
        title={sidebarCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <div className="flex flex-col gap-0.5 flex-1">
        {reportLinks.map((item) => {
          if (item.children) {
            const expanded = expandedGroups.has(item.id) && !sidebarCollapsed
            const controlsId = `${submenuId}-${item.id}`
            const active = item.children.some(({ to }) => pathname === to || pathname.startsWith(`${to}/`))
            const open = () => {
              if (collapsed) setCollapsed(false)
              setGroupExpanded(item.id, true)
            }
            return (
              <div key={item.id} onPointerLeave={(event) => { if (event.pointerType !== 'touch') closeGroup(item.id) }} onKeyDown={(event) => {
                if (event.key === 'Escape') {
                  closeGroup(item.id)
                  event.currentTarget.querySelector('button')?.focus()
                }
              }}>
                <button
                  type="button"
                  aria-label={item.label}
                  aria-expanded={expanded}
                  aria-controls={controlsId}
                  title={sidebarCollapsed ? item.label : undefined}
                  onPointerEnter={(event) => {
                    if (event.pointerType !== 'touch') {
                      setHoveredGroup(item.id)
                      setGroupExpanded(item.id, true)
                    }
                  }}
                  onClick={() => {
                    if (sidebarCollapsed) open()
                    else setGroupExpanded(item.id, !expanded)
                  }}
                  className={[
                    'nav-link min-h-10 w-full text-left text-control 3xl:py-2.5',
                    sidebarCollapsed ? 'justify-center px-0' : '',
                    active ? 'nav-link-active' : '',
                  ].join(' ')}
                >
                  <span className="flex-shrink-0">{item.icon}</span>
                  {!sidebarCollapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      <ChevronDown
                        size={14}
                        aria-hidden="true"
                        className={`flex-shrink-0 transition-transform duration-200 ${expanded ? '' : '-rotate-90'}`}
                      />
                    </>
                  )}
                </button>
                <div id={controlsId} hidden={!expanded}>
                  <div className="ml-5 mt-1 flex flex-col gap-0.5 border-l border-apple-divider/80 pl-2">
                    {item.children.map((child) => (
                      <NavLink
                        key={child.to}
                        to={child.to}
                        aria-label={'ariaLabel' in child ? child.ariaLabel : child.label}
                        className={({ isActive }) =>
                          ['nav-link 3xl:text-control 3xl:py-2.5', isActive ? 'nav-link-active' : ''].join(' ')
                        }
                      >
                        {child.label}
                      </NavLink>
                    ))}
                  </div>
                </div>
              </div>
            )
          }

          const { to, icon, label } = item

          return (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              title={sidebarCollapsed ? label : undefined}
              className={({ isActive }) =>
                ['nav-link min-h-10',
                 sidebarCollapsed ? 'justify-center px-0' : '',
                 isActive ? 'nav-link-active' : '',
                 '3xl:text-control 3xl:py-2.5',
                ].join(' ')
              }
            >
              <span className="flex-shrink-0">{icon}</span>
              {!sidebarCollapsed && <span>{label}</span>}
            </NavLink>
          )
        })}
        {!me.isError && canViewAuditLogs(me.data) && (
          <NavLink to="/audit-logs" title={sidebarCollapsed ? '감사로그' : undefined}
            className={({ isActive }) => ['nav-link min-h-10 3xl:text-control 3xl:py-2.5', sidebarCollapsed ? 'justify-center px-0' : '', isActive ? 'nav-link-active' : ''].join(' ')}>
            <ShieldCheck size={16} className="flex-shrink-0" />
            {!sidebarCollapsed && <span>감사로그</span>}
          </NavLink>
        )}
      </div>

      <div className={['mt-auto pt-4 border-t border-apple-divider/60 flex flex-col', sidebarCollapsed ? 'items-center' : ''].join(' ')}>
        <ThemeToggle collapsed={sidebarCollapsed} />

        {loginRequired && (
          <>
            <div className="w-full border-t border-apple-divider/50 my-2" />

            {sidebarCollapsed ? (
              <button
                onClick={() => logout()}
                disabled={isLoggingOut}
                title={username ? `${username} · LOGOUT` : 'LOGOUT'}
                className="flex items-center justify-center w-8 h-8 rounded-xl text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
              >
                <LogOut size={14} />
              </button>
            ) : (
              <button
                onClick={() => logout()}
                disabled={isLoggingOut}
                className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-control font-medium tracking-wide text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
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
