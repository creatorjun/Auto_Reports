// frontend/src/domain/SlaViolationSort.ts
import { getIssueTypeLabel } from './IssueTypeLabel'
import { slaIssueType } from './SlaViolationFilters'
import type { SlaViolationTicket } from './SlaViolationReport'

export type SlaViolationSortKey = 'key' | 'summary' | 'issue_type' | 'created_at' | 'elapsed_days'
export interface SlaViolationSort {
  key: SlaViolationSortKey
  direction: 'asc' | 'desc'
}

const COLLATOR = new Intl.Collator('ko-KR', { numeric: true, sensitivity: 'base' })

export function sortSlaViolationTickets(tickets: SlaViolationTicket[], sort: SlaViolationSort | null): SlaViolationTicket[] {
  if (!sort) return tickets
  return [...tickets].sort((left, right) => {
    let result: number
    if (sort.key === 'elapsed_days') result = left.elapsed_days - right.elapsed_days
    else if (sort.key === 'created_at') result = Date.parse(left.created_at) - Date.parse(right.created_at)
    else if (sort.key === 'issue_type') result = COLLATOR.compare(getIssueTypeLabel(slaIssueType(left)), getIssueTypeLabel(slaIssueType(right)))
    else result = COLLATOR.compare(left[sort.key], right[sort.key])
    return sort.direction === 'asc' ? result : -result
  })
}
