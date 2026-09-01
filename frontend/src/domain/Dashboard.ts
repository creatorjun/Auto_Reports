// frontend/src/domain/Dashboard.ts
export interface SlaViolationIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

export interface ViolationEntry {
  stage: string
  count: number
  rate: number
  issue_details?: SlaViolationIssue[]
}

export interface SlaDelayIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

export interface MonthlyEntry {
  month: string
  year: number
  month_num: number
  rate: number
  met: number
  total: number
  by_type?: Record<string, { met: number; total: number }>
  always_included?: { met: number; total: number } | null
}

export type Semester = 'h1' | 'h2'

export interface MonthlyCountEntry {
  month: string
  year: number
  month_num: number
  count: number
  by_type?: Record<string, number>
  always_included?: number | null
}

export interface CreatedIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

export interface ResolvedIssue {
  key: string
  summary: string
  type: string
  status: string
  resolved: string
}

export interface WorkTypeOpenWidget {
  key: string
  label: string
  count: number
  issues: IncompleteIssue[]
}

export interface RedeploymentIssue {
  key: string
  summary: string
  type: string
  priority: string
  resolved: string
  month: string
  cause: string
  assignee: string
  partners: string[]
}

export interface RedeploymentMonthlyEntry {
  month: string
  year: number
  month_num: number
  total: number
  by_type: Record<string, number>
}

export interface RedeploymentAnalytics {
  resolved_total: number
  redeployment_total: number
  redeployment_rate: number
  analytics_total: number
  classification_complete: boolean
  monthly: RedeploymentMonthlyEntry[]
  by_cause: Record<string, number>
  by_assignee: Record<string, number>
  partner_matrix: Record<string, Record<string, number>>
  latest_issues: RedeploymentIssue[]
  source_jqls: Record<string, string>
}

export interface StatusIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
  elapsed_days: number
}

export type ReviewIssue = StatusIssue
export type DataRequestIssue = StatusIssue
export type ResultPendingIssue = StatusIssue
export type IncompleteIssue = StatusIssue
