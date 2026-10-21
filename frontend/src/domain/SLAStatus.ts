// frontend/src/domain/SLAStatus.ts
export interface SlaStatusMetric {
  sla_id: string
  sla_name: string
  goal_millis: number
  remaining_millis: number
  remaining_percent: number
  paused: boolean
}

export interface SlaStatusTicket {
  key: string
  summary: string
  status: string
  assignee: string
  slas: SlaStatusMetric[]
  issue_type?: string | null
  created_at?: string | null
  elapsed_days?: number | null
  customer?: string | null
  partners?: string[] | null
  reporter?: string | null
  tac_assignee?: string | null
  status_durations?: { status: string; hours: number }[] | null
  status_durations_basis?: 'resolution_sla'
  status_duration_calendar?: string | null
  warnings?: string[]
}

export interface SlaStatusSnapshot {
  generated_at: string
  threshold_percent: number
  ticket_count: number
  sla_count: number
  tickets: SlaStatusTicket[]
  refresh_in_progress: boolean
  stale: boolean
  refresh_error: string | null
}

export type SlaStatusScope = 'all' | 'urgent' | 'running' | 'paused'
export type SlaStatusSort = 'remaining_percent' | 'remaining_millis' | 'key'

export interface SlaStatusFilters {
  scope: SlaStatusScope
  search: string
  status: string
  stage: string
  sort: SlaStatusSort
}
