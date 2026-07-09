// frontend/src/domain/Job.ts
export interface TriggerAccepted {
  job_id: string
  message: string
}

export interface JobStatus {
  job_id: string
  status: 'running' | 'done' | 'error'
  report_id: number | null
  error: string | null
}

export interface TriggerParams {
  start_date?: string
  end_date?: string
}
