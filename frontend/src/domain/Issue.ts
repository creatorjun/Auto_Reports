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

export type ElapsedDaysComparison = 'gte' | 'lte'

export function filterRecentIssuesByElapsedDays(
  issues: RecentIssue[],
  thresholdDays: number | null,
  comparison: ElapsedDaysComparison = 'gte',
): RecentIssue[] {
  return thresholdDays === null ? issues : issues.filter((issue) => comparison === 'gte'
    ? issue.elapsed_days >= thresholdDays
    : issue.elapsed_days <= thresholdDays)
}
