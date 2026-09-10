// frontend/src/domain/Issue.ts
export interface BaseIssue {
  key:          string
  summary:      string
  type:         string
  status:       string
  stage_index:  number
  created:      string
  elapsed_days: number
  reporter:     string
  tac_team:     string
}

export interface RecentIssue extends BaseIssue {
  tac_assignee?: string | null
}

export function filterRecentIssuesByElapsedDays(issues: RecentIssue[], maxDays: number | null): RecentIssue[] {
  return maxDays === null ? issues : issues.filter((issue) => issue.elapsed_days <= maxDays)
}
