// frontend/src/presentation/components/layout/Sidebar.tsx
import { useCallback, useEffect, useId, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, List, Clock, ListChecks, Building2, HardDrive, Users, ChevronDown, ChevronLeft, ChevronRight, LogOut, CalendarRange, ShieldCheck, Newspaper, Bell, UserRound, X } from 'lucide-react'
import { useAuthStore } from '@/presentation/state/authStore'
import { useLogout, useMe } from '@/presentation/hooks/useAuth'
import { canViewAuditLogs, canViewJiraNotifications, canViewSiteManagement } from '@/domain/Auth'
import JiraNotificationsPanel from '@/presentation/components/notifications/JiraNotificationsPanel'
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
  { to: '/security-news', label: '보안 뉴스', icon: <Newspaper size={16} /> },
]

interface Props {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export default function Sidebar({ collapsed, setCollapsed, mobileOpen = false, onCloseMobile }: Props) {
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
  const { loginRequired, username, accessToken } = useAuthStore()
  const { mutate: logout, isPending: isLoggingOut } = useLogout()
  const me = useMe()
  const profile = accessToken && !me.isError ? me.data : undefined
  const siteManagementVisible = !me.isPending && canViewSiteManagement(profile)
  const accountLabel = profile?.login_required
    ? profile.auth_provider === 'jira'
      ? profile.email_address?.trim() || '이메일 비공개'
      : `ID: ${profile.username}`
    : null
  const allowed = !!accessToken && canViewJiraNotifications(profile)
  const [notification, setNotification] = useState<{ trigger: HTMLButtonElement; token: string } | null>(null)
  const panelId = useId()
  const expanded = allowed && notification?.token === accessToken
  const closeNotifications = useCallback(() => setNotification(null), [])
  useEffect(() => { if (!mobileOpen) closeNotifications() }, [mobileOpen, closeNotifications])
  useEffect(() => { closeNotifications() }, [pathname, closeNotifications])
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const media = window.matchMedia('(min-width: 1280px)')
    media.addEventListener('change', closeNotifications)
    return () => media.removeEventListener('change', closeNotifications)
  }, [closeNotifications])

  return (
    <aside
      className={[
        sidebarCollapsed ? 'w-14 3xl:w-16' : 'w-56 xl:w-60 2xl:w-64 3xl:w-72',
        'bg-apple-surface border-r border-apple-divider/80',
        'flex flex-col whitespace-nowrap py-5 3xl:py-7 px-2 3xl:px-3',
        'transition-all duration-250 ease-in-out flex-shrink-0',
      ].join(' ')}
    >
      {onCloseMobile && <button type="button" onClick={onCloseMobile} aria-label="계정 메뉴 닫기" className="mb-2 self-end rounded-xl p-2 text-apple-mid hover:bg-apple-gray xl:hidden"><X size={18} aria-hidden="true" /></button>}
      <button
        onClick={() => {
          setExpandedGroups(new Set())
          setHoveredGroup(null)
          setCollapsed(!sidebarCollapsed)
        }}
        className="hidden xl:flex shrink-0 items-center justify-center w-8 h-8 3xl:w-10 3xl:h-10 rounded-xl text-apple-light hover:bg-apple-gray hover:text-apple-dark transition-all duration-200 mb-2 self-end"
        title={sidebarCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <div className="flex min-h-0 flex-col gap-0.5 flex-1 overflow-y-auto">
        {reportLinks.filter((item) => item.to !== '/sites' || siteManagementVisible).map((item) => {
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
                          ['nav-link 3xl:py-2.5', isActive ? 'nav-link-active' : ''].join(' ')
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
              aria-label={label}
              end={to === '/'}
              title={sidebarCollapsed ? label : undefined}
              className={({ isActive }) =>
                ['nav-link min-h-10',
                 sidebarCollapsed ? 'justify-center px-0' : '',
                 isActive ? 'nav-link-active' : '',
                 '3xl:py-2.5',
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
            className={({ isActive }) => ['nav-link min-h-10 3xl:py-2.5', sidebarCollapsed ? 'justify-center px-0' : '', isActive ? 'nav-link-active' : ''].join(' ')}>
            <ShieldCheck size={16} className="flex-shrink-0" />
            {!sidebarCollapsed && <span>감사로그</span>}
          </NavLink>
        )}
      </div>

      <div className={['mt-auto shrink-0 pt-4 border-t border-apple-divider/60 flex flex-col', sidebarCollapsed ? 'items-center' : ''].join(' ')}>
        <ThemeToggle collapsed={sidebarCollapsed} />

        {loginRequired && (
          <>
            <div className="w-full border-t border-apple-divider/50 my-2" />

            {accountLabel && (sidebarCollapsed ? <button type="button" onClick={() => setCollapsed(false)} aria-label={`로그인 사용자 ${profile?.display_name ?? ''} · ${accountLabel}`} title={`${profile?.display_name ?? ''} · ${accountLabel}`} className="mb-1 flex h-9 w-9 items-center justify-center rounded-xl text-apple-mid hover:bg-apple-gray"><UserRound size={16} aria-hidden="true" /></button>
              : <div aria-label="로그인 사용자" className="min-w-0 px-3 pb-2 text-caption text-apple-mid">{profile?.display_name && <p className="truncate font-medium text-apple-dark" title={profile.display_name}>{profile.display_name}</p>}<p className="truncate" title={accountLabel}>{accountLabel}</p></div>)}
            {allowed && <button type="button" aria-label="Jira 알림" aria-haspopup="dialog" aria-expanded={expanded} aria-controls={panelId} title={sidebarCollapsed ? 'Jira 알림' : undefined}
              onClick={(event) => setNotification(expanded || !accessToken ? null : { trigger: event.currentTarget, token: accessToken })}
              className={`mb-1 flex min-h-9 items-center rounded-xl text-control focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${sidebarCollapsed ? 'w-9 justify-center' : 'w-full gap-2 px-3 py-2'} ${expanded ? 'bg-brand-50 text-brand-700' : 'text-apple-mid hover:bg-apple-gray'}`}><Bell size={16} className="shrink-0" aria-hidden="true" />{!sidebarCollapsed && <span>Jira 알림</span>}</button>}

            {sidebarCollapsed ? (
              <button
                aria-label="로그아웃"
                onClick={() => logout()}
                disabled={isLoggingOut}
                title={username ? `${username} · LOGOUT` : 'LOGOUT'}
                className="flex items-center justify-center w-8 h-8 rounded-xl text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
              >
                <LogOut size={14} />
              </button>
            ) : (
              <button
                aria-label="로그아웃"
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
      {expanded && notification && <JiraNotificationsPanel key={notification.token} id={panelId} trigger={notification.trigger} sessionToken={notification.token} sidebarCollapsed={sidebarCollapsed} onClose={closeNotifications} />}
    </aside>
  )
}
