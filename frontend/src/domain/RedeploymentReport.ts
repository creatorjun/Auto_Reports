// frontend/src/domain/RedeploymentReport.ts
export interface RedeploymentTicket {
  key: string
  summary: string
  issue_type: string
  status: string
  closed: boolean
  created_at: string
  resolved_at: string | null
  completion_month: string | null
  cause: string | null
  reason: string | null
  repatch_count: number | null
  customer: string | null
  partners: string[]
  assignee: string | null
  reporter: string | null
}

export interface RedeploymentReport {
  id: number
  period_start: string
  generated_at: string
  generated_by: string
  source_jql: string
  tickets: RedeploymentTicket[]
  warnings: string[]
}

export type RedeploymentScope = 'all' | 'active' | 'closed'
