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
