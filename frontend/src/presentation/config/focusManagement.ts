// frontend/src/presentation/config/focusManagement.ts
export const FOCUS_MANAGEMENT_LABEL = '집중 관리 항목'

export const FOCUS_MANAGEMENT_LINKS = [
  { to: '/redeployments', label: '재배포 현황' },
  { to: '/sla-violations', label: 'SLA 현황' },
  { to: '/sla-dashboard', label: '장기 이슈' },
  { to: '/issues', label: '전체 이슈' },
] as const

export function isFocusManagementPath(pathname: string) {
  return FOCUS_MANAGEMENT_LINKS.some(({ to }) => pathname === to || pathname.startsWith(`${to}/`))
}
