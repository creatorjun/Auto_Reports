// frontend/src/domain/CLevelReport.ts
export type CLevelPeriod = 'week' | 'month'
export type CLevelType = 'service' | 'incident' | 'improvement'
export type CLevelMetric = 'initial_response' | 'resolution'
export type CLevelOwner = 'TAC' | '고객·파트너' | '연구소' | '기타'
export type CLevelAgeBucketId = '1-3' | '3-6' | '6-12' | '12+'

export interface CLevelCounts {
  created: number | null
  resolved: number | null
  unresolved: number | null
  resolution_rate: number | null
  average_resolution_days: number | null
}

export interface CLevelCard extends CLevelCounts {
  type: CLevelType | 'all'
  label: string
  previous: CLevelCounts
  delta: { created: number | null; resolved: number | null; unresolved: number | null }
}

export interface CLevelTrend {
  label: string
  start_date: string
  end_date: string
  created: number | null
  resolved: number | null
  unresolved: number | null
  by_type: Array<{ type: CLevelType; label: string; created: number | null; resolved: number | null; unresolved: number | null }>
}

export interface CLevelAgeBucket {
  id: CLevelAgeBucketId
  label: string
  min_months: number
  max_months: number | null
  count: number | null
  known_count?: number
  customer_count: number | null
  by_type: Record<CLevelType, number | null>
}

export interface CLevelCustomerIssue {
  key: string
  type: CLevelType
  bucket: CLevelAgeBucketId
  age_days: number
  status: string
  tac_assignee: string | null
  partner_names: string[]
}

export interface CLevelCustomer {
  customer_key: string
  customer_name: string
  partners: string[]
  tac_assignees: string[]
  total: number
  by_type: Record<CLevelType, number>
  buckets: Record<CLevelAgeBucketId, number>
  oldest_days: number
  dominant_status: string
  issue_keys: string[]
  issues: CLevelCustomerIssue[]
}

export interface CLevelSlaMeasure {
  violations: number | null
  evaluated: number | null
  met: number | null
  compliance_rate: number | null
}

export interface CLevelSlaType {
  type: CLevelType
  label: string
  initial_response: CLevelSlaMeasure
  resolution: CLevelSlaMeasure
}

export interface CLevelViolation {
  id: string
  issue_key: string
  summary: string
  type: CLevelType
  type_label: string
  customer_name: string | null
  metric: CLevelMetric
  cycle_id: string
  goal_hours: number | null
  elapsed_hours: number | null
  excess_hours: number | null
  breach_at: string | null
  status: string
  status_at_breach: string | null
  owner_at_breach: CLevelOwner | null
  paused: boolean | null
  is_ongoing: boolean
}

export interface CLevelTimelineSegment {
  id: string
  status: string
  status_id: string | null
  status_category: string | null
  owner: CLevelOwner
  start_at: string
  end_at: string
  duration_hours: number | null
  is_current: boolean
  breached_metrics: string[]
}

export interface CLevelSlaCycle {
  metric: CLevelMetric
  cycle_id: string
  start_at: string | null
  stop_at: string | null
  breach_at: string | null
  goal_hours: number | null
  elapsed_hours: number | null
  remaining_hours: number | null
  excess_hours: number | null
  breached: boolean | null
  paused: boolean | null
  ongoing: boolean
  historical_elapsed_known: boolean
}

export interface CLevelIssue {
  key: string
  summary: string
  issue_type: string
  type: CLevelType
  type_label: string
  customer_name: string | null
  partner_names: string[]
  reporter: string | null
  assignee: string | null
  tac_assignee: string | null
  created_at: string
  updated_at: string | null
  status: string
  status_category: string | null
  history_complete: boolean
  reopen_count: number | null
  age_days: number | null
  age_bucket: string | null
  is_unresolved: boolean | null
  first_response_at: string | null
  first_response_source?: 'sla_cycle' | 'jira_first_response_field' | null
  timeline: CLevelTimelineSegment[]
  owner_hours: Record<CLevelOwner, number | null>
  sla_cycles: CLevelSlaCycle[]
  warnings: string[]
}

export interface CLevelCommentInput {
  delay_reason: string
  action_taken: string
  prevention_plan: string
  included: boolean
}

export interface CLevelComment extends CLevelCommentInput {
  issue_key?: string
  updated_at?: string
  updated_by?: string
}

export interface CLevelSnapshotSummary {
  id: number
  title: string
  period: CLevelPeriod
  start_date: string
  end_date: string
  as_of: string
  saved_at: string
  saved_by: string
}

export interface CLevelReport {
  period: CLevelPeriod
  start_date: string
  end_date: string
  as_of: string
  previous_start_date: string
  previous_end_date: string
  generated_at: string
  policy_version: string
  policy_labels: string[]
  warnings: string[]
  report_token: string | null
  summary: CLevelCard[]
  trend: CLevelTrend[]
  long_term: {
    buckets: CLevelAgeBucket[]
    customers: CLevelCustomer[]
    unknown_status_issue_count?: number
    unassigned_customer_issue_count?: number
    previous_total?: number | null
    delta_total?: number | null
    previous_over_12_months?: number | null
    delta_over_12_months?: number | null
  }
  sla: {
    by_type: CLevelSlaType[]
    violation_ticket_count: number | null
    violation_event_count: number | null
    delay_reasons: Array<{ status: string; owner: CLevelOwner | null; count: number; percentage: number | null }>
    coverage?: { known_cycles: number; unknown_cycles: number; issues_without_sla: number }
  }
  violations: CLevelViolation[]
  issues: CLevelIssue[]
  comments: Record<string, CLevelComment>
  snapshot?: CLevelSnapshotSummary
}
