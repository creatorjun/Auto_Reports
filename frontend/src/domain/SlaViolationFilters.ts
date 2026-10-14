// frontend/src/domain/SlaViolationFilters.ts
import type { Semester } from './Dashboard'
import { isDashboardMonthInSemester } from './DashboardIssueTypePolicy'
import { sortDashboardStatuses } from './DashboardStatusPolicy'
import type { SlaViolationTicket } from './SlaViolationReport'

export const UNKNOWN_SLA_ISSUE_TYPE = '확인 불가'

export function slaIssueType(ticket: SlaViolationTicket): string {
  return ticket.issue_type?.trim() || UNKNOWN_SLA_ISSUE_TYPE
}

function slaCurrentStatus(ticket: SlaViolationTicket): string {
  return ticket.current_status.trim() || '확인 불가'
}

export function slaViolationFilterOptions(tickets: SlaViolationTicket[]) {
  return {
    issueTypes: [...new Set(tickets.map(slaIssueType))].sort((left, right) => left.localeCompare(right, 'ko-KR')),
    statuses: sortDashboardStatuses(tickets.map(slaCurrentStatus)),
    unknownTypeCount: tickets.filter((ticket) => !ticket.issue_type?.trim()).length,
  }
}

export function filterSlaViolationTickets(
  tickets: SlaViolationTicket[],
  selectedTypes: ReadonlySet<string> | null,
  selectedStatuses: ReadonlySet<string> | null,
  selectedSemester: Semester | null,
): SlaViolationTicket[] {
  if (selectedTypes === null && selectedStatuses === null && selectedSemester === null) return tickets
  return tickets.filter((ticket) => {
    const kstMonth = new Date(Date.parse(ticket.created_at) + 9 * 60 * 60 * 1000).getUTCMonth() + 1
    return (selectedTypes === null || selectedTypes.has(slaIssueType(ticket)))
      && (selectedStatuses === null || selectedStatuses.has(slaCurrentStatus(ticket)))
      && (selectedSemester === null || isDashboardMonthInSemester(selectedSemester, kstMonth))
  })
}
