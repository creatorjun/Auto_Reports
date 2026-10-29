// frontend/src/domain/IssueManagement.ts
import type { RecentIssue } from './Issue'
import type { Semester } from './Dashboard'
import { isDashboardMonthInSemester } from './DashboardIssueTypePolicy'

export interface IssueManagementSnapshot {
  issues: RecentIssue[]
  initialized: boolean
  refreshing: boolean
  synced_at: string | null
  error: string | null
  status_transitions?: Record<string, Record<string, string>>
  status_transition_days?: Record<string, Record<string, number>>
  transition_history_ready?: boolean
}

export function filterManagedIssues(
  issues: RecentIssue[],
  types: ReadonlySet<string> | null,
  statuses: ReadonlySet<string> | null,
  semester: Semester | null,
  year: number | null,
): RecentIssue[] {
  if (types === null && statuses === null && semester === null && year === null) return issues
  return issues.filter((issue) => (
    (types === null || types.has(issue.type))
    && (statuses === null || statuses.has(issue.status))
    && (year === null || Number(issue.created.slice(0, 4)) === year)
    && (semester === null || isDashboardMonthInSemester(semester, Number(issue.created.slice(5, 7))))
  ))
}
