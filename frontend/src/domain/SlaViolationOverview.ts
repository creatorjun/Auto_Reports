// frontend/src/domain/SlaViolationOverview.ts
import { normalizeSearchText } from './Search'
import { slaCurrentStatus, slaIssueType } from './SlaViolationFilters'
import type { SlaViolationMetric, SlaViolationReport, SlaViolationTicket } from './SlaViolationReport'

export type SlaViolationScope = 'all' | SlaViolationMetric | 'both'
export type SlaOverviewPeriod = Pick<SlaViolationReport, 'period' | 'start_date' | 'end_date'>

export interface SlaViolationBucket {
  key: string
  label: string
  count: number
}

export function filterSlaViolationScope(tickets: SlaViolationTicket[], scope: SlaViolationScope): SlaViolationTicket[] {
  return tickets.filter((ticket) => {
    const initial = ticket.breaches.some((breach) => breach.metric === 'initial_response')
    const resolution = ticket.breaches.some((breach) => breach.metric === 'resolution')
    return scope === 'all' ? initial || resolution : scope === 'both' ? initial && resolution : scope === 'initial_response' ? initial : resolution
  })
}

export function slaViolationCounts(tickets: SlaViolationTicket[]): Record<SlaViolationScope, number> {
  return {
    all: filterSlaViolationScope(tickets, 'all').length,
    initial_response: filterSlaViolationScope(tickets, 'initial_response').length,
    resolution: filterSlaViolationScope(tickets, 'resolution').length,
    both: filterSlaViolationScope(tickets, 'both').length,
  }
}

export function slaViolationStatuses(tickets: SlaViolationTicket[]) {
  const counts = new Map<string, number>()
  for (const ticket of tickets) {
    const status = slaCurrentStatus(ticket)
    counts.set(status, (counts.get(status) ?? 0) + 1)
  }
  return [...counts].map(([status, count]) => ({ status, count }))
    .sort((left, right) => right.count - left.count || left.status.localeCompare(right.status, 'ko-KR'))
}

export function slaViolationBucketKey(ticket: SlaViolationTicket, period: SlaOverviewPeriod['period']): string | null {
  const timestamp = Date.parse(ticket.created_at)
  if (!Number.isFinite(timestamp)) return null
  return new Date(timestamp + 9 * 3600_000).toISOString().slice(0, period === 'year' ? 7 : 10)
}

export function slaViolationTimeline(report: SlaOverviewPeriod, tickets: SlaViolationTicket[]) {
  const buckets = new Map<string, SlaViolationBucket>()
  const start = Date.parse(`${report.start_date}T00:00:00Z`)
  const end = Date.parse(`${report.end_date}T00:00:00Z`)
  for (let timestamp = start; timestamp <= end; timestamp += 86400_000) {
    const date = new Date(timestamp).toISOString().slice(0, 10)
    const key = date.slice(0, report.period === 'year' ? 7 : 10)
    if (!buckets.has(key)) buckets.set(key, {
      key,
      label: report.period === 'year' ? `${Number(date.slice(5, 7))}월` : `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}`,
      count: 0,
    })
  }
  let unassigned = 0
  for (const ticket of tickets) {
    const key = slaViolationBucketKey(ticket, report.period)
    const bucket = key === null ? undefined : buckets.get(key)
    if (bucket) bucket.count++
    else unassigned++
  }
  return { buckets: [...buckets.values()], unassigned }
}

export function filterSlaViolationDetails(
  tickets: SlaViolationTicket[], period: SlaOverviewPeriod['period'], status: string | null, bucket: string | null, search: string,
): SlaViolationTicket[] {
  const term = normalizeSearchText(search)
  return tickets.filter((ticket) => {
    if (status !== null && slaCurrentStatus(ticket) !== status) return false
    if (bucket !== null && slaViolationBucketKey(ticket, period) !== bucket) return false
    if (!term) return true
    const partners = ticket.partners === null ? '확인 불가' : ticket.partners.length ? ticket.partners.join(' ') : '본사'
    return normalizeSearchText([
      ticket.key, ticket.summary, ticket.customer, ticket.assignee, ticket.tac_assignee,
      ticket.reporter, slaIssueType(ticket), slaCurrentStatus(ticket), partners,
    ].filter(Boolean).join(' ')).includes(term)
  })
}
