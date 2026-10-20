// frontend/src/domain/Job.ts
import type { PeriodReportRequest } from '@/domain/ReportPeriod'

export interface TriggerAccepted {
  job_id: string
  message: string
}

export interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'error'
  report_id: number | null
  error: string | null
}

export type TriggerParams = PeriodReportRequest | { rerun_latest: true } | {
  start_date?: string
  end_date?: string
}
