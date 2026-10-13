// frontend/src/infrastructure/api/cLevelReportApi.ts
import client from './client'
import type { CLevelReportGateway } from '@/application/ports/ApplicationServices'
import type { CLevelComment, CLevelReport, CLevelSnapshotSummary } from '@/domain/CLevelReport'

export const cLevelReportApi: CLevelReportGateway = {
  getReport: async (period, date, refresh = false, signal) => {
    const response = await client.get<CLevelReport>('/c-level-report', { params: { period, date, refresh }, signal, timeout: 600_000 })
    return response.data
  },
  saveComment: async (key, reportToken, comment) => {
    const response = await client.put<CLevelComment>(`/c-level-report/comments/${encodeURIComponent(key)}`, { ...comment, report_token: reportToken })
    return response.data
  },
  saveSnapshot: async (reportToken, title) => {
    const response = await client.post<CLevelSnapshotSummary>('/c-level-report/snapshots', { report_token: reportToken, title })
    return response.data
  },
  getSnapshots: async (limit = 20, offset = 0) => {
    const response = await client.get<CLevelSnapshotSummary[]>('/c-level-report/snapshots', { params: { limit, offset } })
    return response.data
  },
  getSnapshot: async (id, signal) => {
    const response = await client.get<CLevelReport>(`/c-level-report/snapshots/${id}`, { signal, timeout: 60_000 })
    return response.data
  },
}
