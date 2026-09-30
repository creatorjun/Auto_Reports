// frontend/src/domain/IssueManagement.ts
import type { RecentIssue } from './Issue'
import type { Semester } from './Dashboard'
import { normalizeSearchText } from './Search'
import { isDashboardMonthInSemester } from './DashboardIssueTypePolicy'

export interface IssueManagementSnapshot {
  issues: RecentIssue[]
  initialized: boolean
  refreshing: boolean
  synced_at: string | null
  error: string | null
}

export type IssueColumn = 'key' | 'summary' | 'status' | 'reporter' | 'tac' | 'tac_assignee' | 'elapsed'
export type IssueColumnFilters = Partial<Record<IssueColumn, string>>

export function filterIssuesByColumns(issues: RecentIssue[], filters: IssueColumnFilters): RecentIssue[] {
  const active = Object.entries(filters).map(([column, value]) => [column, normalizeSearchText(value ?? '')]).filter(([, value]) => value)
  return issues.filter((issue) => active.every(([column, query]) => {
    const value = column === 'tac' ? issue.tac_team
      : column === 'elapsed' ? `${issue.created.slice(0, 10) || '-'} · ${issue.elapsed_days}일`
      : column === 'tac_assignee' ? issue.tac_assignee ?? '-'
      : issue[column as 'key' | 'summary' | 'status' | 'reporter']
    return normalizeSearchText(value ?? '').includes(query)
  }))
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
