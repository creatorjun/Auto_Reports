// frontend/src/infrastructure/api/slaDashboardApi.ts
import client from './client'
import { createBinaryContent } from './binaryContent'
import type { BinaryContent } from '@/application/ports/ApplicationServices'
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
  getCommentImage: async (
    issueKey: string,
    commentId: string,
    attachmentId: string,
  ): Promise<BinaryContent> => {
    const key = encodeURIComponent(issueKey)
    const comment = encodeURIComponent(commentId)
    const attachment = encodeURIComponent(attachmentId)
    const response = await client.get<Blob>(
      `/sla-dashboard/issues/${key}/comments/${comment}/images/${attachment}`,
      { responseType: 'blob' },
    )
    return createBinaryContent(response.data)
  },
}
