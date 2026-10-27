// frontend/src/domain/SlaViolationReport.ts
import type { ReportPeriod } from '@/domain/ReportPeriod'

export type SlaViolationPeriod = Exclude<ReportPeriod, 'day'>
export type SlaViolationMetric = 'initial_response' | 'resolution'

export interface SlaViolationRequest {
  period: SlaViolationPeriod
  date: string
}

export interface SlaViolationBreach {
  metric: SlaViolationMetric
  breached_at: string | null
  status: string | null
}

export interface SlaViolationCycle {
  metric: SlaViolationMetric
  breached: boolean
  ongoing: boolean
  paused: boolean | null
  goal_ms: number | null
  elapsed_ms: number | null
  exceeded_ms: number | null
  started_at: string | null
  stopped_at: string | null
  breached_at: string | null
  status: string | null
}

export interface SlaViolationTicket {
  key: string
  summary: string
  issue_type?: string | null
  created_at: string
  elapsed_days: number
  customer: string | null
  partners: string[] | null
  reporter: string | null
  assignee: string | null
  tac_assignee: string | null
  current_status: string
  status_durations: { status: string; hours: number }[] | null
  status_durations_basis?: 'wall_clock' | 'resolution_sla'
  breaches: SlaViolationBreach[]
  sla_cycles?: SlaViolationCycle[] | null
  warnings: string[]
}

export interface SlaViolationReportSummary {
  id: number
  period: SlaViolationPeriod
  selected_date: string
  start_date: string
  end_date: string
  generated_at: string
  generated_by: string
  ticket_count: number
  initial_response_count: number
  resolution_count: number
}

export interface SlaViolationReport extends SlaViolationReportSummary {
  tickets: SlaViolationTicket[]
  warnings: string[]
}
