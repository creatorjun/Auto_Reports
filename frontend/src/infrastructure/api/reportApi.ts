// frontend/src/infrastructure/api/reportApi.ts
import client from './client'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { TriggerAccepted, JobStatus, TriggerParams } from '@/domain/Job'
import type { AppConfig } from '@/domain/Config'

export type { TriggerAccepted, JobStatus, TriggerParams, AppConfig }

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
  trigger: async (params?: TriggerParams): Promise<TriggerAccepted> => {
    const res = await client.post<TriggerAccepted>('/trigger/', params ?? {})
    return res.data
  },
  getJobStatus: async (jobId: string): Promise<JobStatus> => {
    const res = await client.get<JobStatus>(`/trigger/${jobId}/status`)
    return res.data
  },
  getJobStreamUrl: (jobId: string, token?: string): string => {
    const base = '/api/v1'
    const path = `${base}/trigger/${jobId}/stream`
    return token ? `${path}?token=${encodeURIComponent(token)}` : path
  },
  delete: async (id: number): Promise<void> => {
    await client.delete(`/reports/${id}`)
  },
  getConfig: async (): Promise<AppConfig> => {
    const res = await client.get<AppConfig>('/config')
    return res.data
  },
}
