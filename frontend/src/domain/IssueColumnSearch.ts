// frontend/src/domain/IssueColumnSearch.ts
import type { RecentIssue } from './Issue'
import { normalizeSearchText } from './Search'

export type IssueColumn = 'key' | 'summary' | 'status' | 'reporter' | 'tac' | 'tac_assignee' | 'elapsed'
export type IssueColumnFilters = Partial<Record<IssueColumn, string>>

export function filterIssuesByColumns(issues: RecentIssue[], filters: IssueColumnFilters): RecentIssue[] {
  const active = Object.entries(filters).map(([column, value]) => [column, normalizeSearchText(value ?? '')]).filter(([, value]) => value)
  if (active.length === 0) return issues
  return issues.filter((issue) => active.every(([column, query]) => {
    const value = column === 'tac' ? issue.tac_team
      : column === 'elapsed' ? `${issue.created.slice(0, 10) || '-'} · ${issue.elapsed_days}일`
      : column === 'tac_assignee' ? issue.tac_assignee ?? '-'
      : issue[column as 'key' | 'summary' | 'status' | 'reporter']
    return normalizeSearchText(value ?? '').includes(query)
  }))
}
