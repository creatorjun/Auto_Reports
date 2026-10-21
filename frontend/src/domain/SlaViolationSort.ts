// frontend/src/domain/SlaViolationSort.ts
import { getIssueTypeLabel } from './IssueTypeLabel'
import { slaIssueType } from './SlaViolationFilters'
import { slaViolationLabel } from './SlaViolationMetric'
import type { SlaViolationTicket } from './SlaViolationReport'

export type SlaViolationSortKey = 'key' | 'summary' | 'issue_type' | 'violation' | 'created_at' | 'elapsed_days'
export interface SlaViolationSort {
  key: SlaViolationSortKey
  direction: 'asc' | 'desc'
}

const COLLATOR = new Intl.Collator('ko-KR', { numeric: true, sensitivity: 'base' })

export function sortSlaViolationTickets(tickets: SlaViolationTicket[], sort: SlaViolationSort | null): SlaViolationTicket[] {
  if (!sort) return tickets
  const key = sort.key
  if (key === 'created_at') {
    return tickets.map((ticket) => ({ ticket, value: Date.parse(ticket.created_at) }))
      .sort((left, right) => sort.direction === 'asc' ? left.value - right.value : right.value - left.value)
      .map(({ ticket }) => ticket)
  }
  if (key === 'issue_type' || key === 'violation') {
    return tickets.map((ticket) => ({
      ticket,
      value: key === 'issue_type' ? getIssueTypeLabel(slaIssueType(ticket)) : slaViolationLabel(ticket),
    })).sort((left, right) => sort.direction === 'asc' ? COLLATOR.compare(left.value, right.value) : COLLATOR.compare(right.value, left.value))
      .map(({ ticket }) => ticket)
  }
  return [...tickets].sort((left, right) => {
    let result: number
    if (key === 'elapsed_days') result = left.elapsed_days - right.elapsed_days
    else result = COLLATOR.compare(left[key], right[key])
    return sort.direction === 'asc' ? result : -result
  })
}
