// frontend/src/application/services/slaStatus.ts
import type { SlaStatusFilters, SlaStatusMetric, SlaStatusScope, SlaStatusTicket } from '@/domain/SLAStatus'

const collator = new Intl.Collator('ko-KR', { numeric: true, sensitivity: 'base' })
const normalized = (value: string) => value.normalize('NFKC').toLocaleLowerCase('ko-KR')

export function defaultSlaStatusFilters(): SlaStatusFilters {
  return { scope: 'all', search: '', status: '', stage: '', sort: 'remaining_percent' }
}

function matchesScope(sla: SlaStatusMetric, scope: SlaStatusScope): boolean {
  if (scope === 'urgent') return sla.remaining_percent < 10
  if (scope === 'running') return !sla.paused
  if (scope === 'paused') return sla.paused
  return true
}

export function slaStatusCounts(tickets: SlaStatusTicket[]): Record<SlaStatusScope, number> {
  return {
    all: tickets.length,
    urgent: tickets.filter((ticket) => ticket.slas.some((sla) => matchesScope(sla, 'urgent'))).length,
    running: tickets.filter((ticket) => ticket.slas.some((sla) => matchesScope(sla, 'running'))).length,
    paused: tickets.filter((ticket) => ticket.slas.some((sla) => matchesScope(sla, 'paused'))).length,
  }
}

export function slaStatusFilterOptions(tickets: SlaStatusTicket[]) {
  const stages = new Map<string, string>()
  for (const ticket of tickets) for (const sla of ticket.slas) stages.set(sla.sla_id, sla.sla_name)
  return {
    statuses: [...new Set(tickets.map((ticket) => ticket.status))].sort(collator.compare),
    stages: [...stages].map(([id, name]) => ({ id, name })).sort((left, right) => collator.compare(left.name, right.name)),
  }
}

export function filterSlaStatusTickets(tickets: SlaStatusTicket[], filters: SlaStatusFilters): SlaStatusTicket[] {
  const terms = normalized(filters.search).trim().split(/\s+/u).filter(Boolean)
  const metric = filters.sort
  const result: { ticket: SlaStatusTicket; minimum: number }[] = []
  for (const ticket of tickets) {
    if (filters.status && ticket.status !== filters.status) continue
    const slas = ticket.slas.filter((sla) => (!filters.stage || sla.sla_id === filters.stage) && matchesScope(sla, filters.scope))
      .sort((left, right) => left.remaining_percent - right.remaining_percent || left.remaining_millis - right.remaining_millis || collator.compare(left.sla_id, right.sla_id))
    if (slas.length === 0) continue
    if (terms.length) {
      const haystack = normalized([ticket.key, ticket.summary, ticket.status, ticket.assignee, ...slas.map((sla) => sla.sla_name)].join(' '))
      if (!terms.every((term) => haystack.includes(term))) continue
    }
    result.push({
      ticket: { ...ticket, slas },
      minimum: metric === 'key' ? 0 : Math.min(...slas.map((sla) => sla[metric])),
    })
  }
  return result.sort((left, right) => {
    const difference = left.minimum - right.minimum
    return difference || collator.compare(left.ticket.key, right.ticket.key)
  }).map(({ ticket }) => ticket)
}
