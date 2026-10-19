// frontend/src/application/services/redeploymentReport.ts
import type { RedeploymentColumn, RedeploymentColumnFilters, RedeploymentReport, RedeploymentScope, RedeploymentTicket } from '@/domain/RedeploymentReport'
import { normalizeSearchText } from '@/domain/Search'

export function redeploymentSummary(tickets: RedeploymentTicket[]) {
  const closed = tickets.filter((ticket) => ticket.closed).length
  const counts = new Map<string, number>()
  for (const ticket of tickets) counts.set(ticket.cause || '원인 미입력', (counts.get(ticket.cause || '원인 미입력') ?? 0) + 1)
  return {
    total: tickets.length, closed, active: tickets.length - closed,
    repatches: tickets.reduce((sum, ticket) => sum + (ticket.repatch_count ?? 0), 0),
    missingCount: tickets.filter((ticket) => ticket.repatch_count === null).length,
    missingReason: tickets.filter((ticket) => !ticket.reason).length,
    causes: [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'ko')),
  }
}

export function redeploymentMonths(report: RedeploymentReport) {
  const current = new Date(new Date(report.generated_at).getTime() + 9 * 3600_000).toISOString().slice(0, 7)
  const [startYear, startMonth] = report.period_start.split('-').map(Number)
  const [endYear, endMonth] = current.split('-').map(Number)
  const counts = new Map<string, number>()
  for (let month = startYear * 12 + startMonth - 1; month <= endYear * 12 + endMonth - 1; month++) {
    counts.set(`${Math.floor(month / 12)}-${String(month % 12 + 1).padStart(2, '0')}`, 0)
  }
  let unassigned = 0
  for (const ticket of report.tickets.filter((item) => item.closed)) {
    if (ticket.completion_month && counts.has(ticket.completion_month)) counts.set(ticket.completion_month, counts.get(ticket.completion_month)! + 1)
    else unassigned++
  }
  return { months: [...counts].map(([month, count]) => ({ month, count })), unassigned }
}

function columnSearchValue(ticket: RedeploymentTicket, column: RedeploymentColumn): string {
  switch (column) {
    case 'ticket': return [ticket.key, ticket.summary, ticket.customer || '고객사 미입력'].join(' ')
    case 'issue_type': return ticket.issue_type
    case 'status': return ticket.status
    case 'cause': return [ticket.cause || '원인 미입력', ticket.reason || '상세 사유 미입력'].join(' ')
    case 'repatch_count': return ticket.repatch_count === null ? '미입력' : `${ticket.repatch_count}회`
    case 'completion_month': return ticket.closed ? ticket.completion_month || '미입력' : '진행 중'
  }
}

export function filterRedeployments(tickets: RedeploymentTicket[], scope: RedeploymentScope, cause: string, query: string, month = '', columnFilters: RedeploymentColumnFilters = {}) {
  const term = normalizeSearchText(query)
  const activeColumns = (Object.entries(columnFilters) as [RedeploymentColumn, string | undefined][])
    .map(([column, value]) => [column, normalizeSearchText(value ?? '')] as const)
    .filter(([, value]) => value)
  return tickets.filter((ticket) =>
    (scope === 'all' || ticket.closed === (scope === 'closed')) &&
    (!month || (ticket.closed && ticket.completion_month === month)) &&
    (!cause || (ticket.cause || '원인 미입력') === cause) &&
    (!term || normalizeSearchText([ticket.key, ticket.summary, ticket.customer, ticket.cause, ticket.reason, ticket.assignee, ...ticket.partners].filter(Boolean).join(' ')).includes(term)) &&
    activeColumns.every(([column, value]) => {
      const text = normalizeSearchText(columnSearchValue(ticket, column))
      return column === 'issue_type' ? text.replace(/\s/g, '').includes(value.replace(/\s/g, '')) : text.includes(value)
    }),
  ).sort((a, b) => Number(a.closed) - Number(b.closed) || b.key.localeCompare(a.key, 'en', { numeric: true }))
}

export function redeploymentIsStale(generatedAt: string, now = new Date()) {
  const local = new Date(now.getTime() + 9 * 3600_000)
  const due = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate(), -1)
  return new Date(generatedAt).getTime() < (now.getTime() >= due ? due : due - 86400_000)
}
