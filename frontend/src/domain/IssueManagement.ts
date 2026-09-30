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
}

export function filterManagedIssues(
  issues: RecentIssue[],
  types: ReadonlySet<string> | null,
  statuses: ReadonlySet<string> | null,
  semester: Semester | null,
  year: number | null,
): RecentIssue[] {
  return issues.filter((issue) => (
    (types === null || types.has(issue.type))
    && (statuses === null || statuses.has(issue.status))
    && (year === null || Number(issue.created.slice(0, 4)) === year)
    && (semester === null || isDashboardMonthInSemester(semester, Number(issue.created.slice(5, 7))))
  ))
}
