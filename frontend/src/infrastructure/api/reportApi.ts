import client from './client'
import type { ReportDetail, ReportSummary } from '@/domain/Report'

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

export interface AppConfig {
  jira_base_url: string
}

export const reportApi = {
  getLatest: async (): Promise<ReportDetail | null> => {
    const res = await client.get<ReportDetail>('/reports/latest')
    return res.data
  },
  getById: async (id: number): Promise<ReportDetail> => {
    const res = await client.get<ReportDetail>(`/reports/${id}`)
    return res.data
  },
  getAll: async (limit = 20, offset = 0): Promise<ReportSummary[]> => {
    const res = await client.get<ReportSummary[]>('/reports/', { params: { limit, offset } })
    return res.data
  },
  trigger: async (): Promise<TriggerAccepted> => {
    const res = await client.post<TriggerAccepted>('/trigger/')
    return res.data
  },
  getJobStatus: async (jobId: string): Promise<JobStatus> => {
    const res = await client.get<JobStatus>(`/trigger/${jobId}/status`)
    return res.data
  },
  delete: async (id: number): Promise<void> => {
    await client.delete(`/reports/${id}`)
  },
  getConfig: async (): Promise<AppConfig> => {
    const res = await client.get<AppConfig>('/config')
    return res.data
  },
}
