// frontend/src/application/services/cLevelReport.ts
import type { CLevelAgeBucketId, CLevelCustomer, CLevelReport, CLevelType, CLevelViolation } from '@/domain/CLevelReport'

export const CLEVEL_TYPES: Array<{ type: CLevelType; label: string; color: string }> = [
  { type: 'service', label: '단순문의', color: '#65b7cf' },
  { type: 'incident', label: '인시던트', color: '#df7373' },
  { type: 'improvement', label: '개선', color: '#aac861' },
]
export const CLEVEL_AGE_BUCKETS: CLevelAgeBucketId[] = ['1-3', '3-6', '6-12', '12+']
export const CLEVEL_OWNER_COLORS: Record<string, string> = { TAC: '#65b7cf', '고객·파트너': '#e4bc56', '연구소': '#b48ed0', '기타': '#8b93a2' }
export const CLEVEL_AGE_COLORS = ['#e8d99e', '#e3b94f', '#df9758', '#d96c6c']

export function cLevelSlaCompliance(report: CLevelReport, metric: 'initial_response' | 'resolution'): number | null {
  const measures = report.sla.by_type.map((entry) => entry[metric])
  if (measures.some((entry) => entry.evaluated === null || entry.met === null)) return null
  const evaluated = measures.reduce((sum, entry) => sum + (entry.evaluated ?? 0), 0)
  return evaluated ? measures.reduce((sum, entry) => sum + (entry.met ?? 0), 0) / evaluated * 100 : null
}

export function cLevelNumber(value: number | null | undefined, suffix = '', digits = 0): string {
  return value == null || !Number.isFinite(value) ? '확인 불가' : `${value.toLocaleString('ko-KR', { maximumFractionDigits: digits })}${suffix}`
}

export function cLevelText(value: string | null | undefined): string {
  const normalized = value?.trim()
  return !normalized || ['미지정', '확인 필요', '알 수 없음'].includes(normalized) ? '확인 불가' : normalized
}

export function cLevelIssueTitle(customer: string | null | undefined, summary: string): string {
  const prefix = `[${cLevelText(customer)}]`
  const title = summary.trim()
  return title.startsWith(prefix) ? title : `${prefix} ${title}`
}

export function cLevelIssueSummary(customer: string | null | undefined, summary: string): string {
  const prefix = `[${cLevelText(customer)}]`
  const title = summary.trim()
  return title.startsWith(prefix) ? title.slice(prefix.length).trimStart() : title
}

export function cLevelDate(value: string | null | undefined): string {
  if (!value) return '확인 불가'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '확인 불가'
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(date)
}

export function cLevelToday(): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}

export function cLevelMetricLabel(metric: string): string {
  return metric === 'initial_response' ? '최초응답' : '해결시간'
}

export function filterCLevelCustomers(customers: CLevelCustomer[], minimumMonths: number): CLevelCustomer[] {
  const start = minimumMonths >= 12 ? 3 : minimumMonths >= 6 ? 2 : minimumMonths >= 3 ? 1 : 0
  const accepted = new Set(CLEVEL_AGE_BUCKETS.slice(start))
  return customers.map((customer) => {
    const issues = customer.issues.filter((issue) => accepted.has(issue.bucket))
    const buckets: Record<CLevelAgeBucketId, number> = { '1-3': 0, '3-6': 0, '6-12': 0, '12+': 0 }
    const by_type: Record<CLevelType, number> = { service: 0, incident: 0, improvement: 0 }
    const statuses: Record<string, number> = {}
    for (const issue of issues) {
      buckets[issue.bucket] += 1
      by_type[issue.type] += 1
      statuses[issue.status] = (statuses[issue.status] ?? 0) + 1
    }
    return {
      ...customer, issues, total: issues.length, buckets, by_type,
      partners: [...new Set(issues.flatMap((issue) => issue.partner_names))],
      tac_assignees: [...new Set(issues.map((issue) => issue.tac_assignee).filter((value): value is string => Boolean(value)))],
      issue_keys: issues.map((issue) => issue.key),
      oldest_days: issues.length ? Math.max(...issues.map((issue) => issue.age_days)) : 0,
      dominant_status: Object.entries(statuses).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ko'))[0]?.[0] ?? '확인 불가',
    }
  }).filter((customer) => customer.total > 0).sort((a, b) => b.total - a.total || b.oldest_days - a.oldest_days || a.customer_name.localeCompare(b.customer_name, 'ko'))
}

export function filterCLevelViolations(violations: CLevelViolation[], metric: string, issueType: string): CLevelViolation[] {
  return violations.filter((item) => (metric === 'all' || item.metric === metric) && (issueType === 'all' || item.type === issueType))
    .sort((a, b) => (b.excess_hours ?? -1) - (a.excess_hours ?? -1) || a.issue_key.localeCompare(b.issue_key) || a.id.localeCompare(b.id))
}

export function cLevelTrendData(report: CLevelReport, issueType: string) {
  return report.trend.map((entry) => {
    const counts = issueType === 'all' ? entry : entry.by_type.find((item) => item.type === issueType)
    return { label: entry.label, created: counts?.created ?? null, resolved: counts?.resolved ?? null, unresolved: counts?.unresolved ?? null }
  })
}

export function cLevelNewBadgeVisible(releasedAt: string | undefined, now = Date.now()): boolean {
  if (!releasedAt) return false
  const released = new Date(releasedAt).getTime()
  return Number.isFinite(released) && now >= released && now < released + 30 * 86400000
}
