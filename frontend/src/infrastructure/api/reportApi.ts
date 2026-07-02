import client from './client'
import type { ReportDetail, ReportSummary } from '@/domain/Report'

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
  trigger: async (): Promise<{ report_id: number; message: string }> => {
    const res = await client.post('/trigger/')
    return res.data
  }
}
