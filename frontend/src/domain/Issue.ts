// frontend/src/domain/Issue.ts
export interface RecentIssue {
  key: string
  summary: string
  type: string
  status: string
  stage_index: number
  created: string
  elapsed_days: number
  reporter: string
  tac_team: string
}
