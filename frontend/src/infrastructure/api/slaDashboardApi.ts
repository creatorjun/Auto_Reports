// frontend/src/infrastructure/api/slaDashboardApi.ts
import client from './client'
import type { SlaDashboardComment, SlaDashboardIssue } from '@/domain/SlaDashboard'

export const slaDashboardApi = {
  getIssues: async (): Promise<SlaDashboardIssue[]> => {
    const response = await client.get<SlaDashboardIssue[]>('/sla-dashboard/issues')
    return response.data
  },
  getComments: async (issueKey: string): Promise<SlaDashboardComment[]> => {
    const key = encodeURIComponent(issueKey)
    const response = await client.get<SlaDashboardComment[]>(`/sla-dashboard/issues/${key}/comments`)
    return response.data
  },
}
