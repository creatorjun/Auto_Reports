// frontend/src/infrastructure/api/slaDashboardApi.ts
import client from './client'
import { createBinaryContent } from './binaryContent'
import type { BinaryContent, CancellationSignal } from '@/application/ports/ApplicationServices'
import type { SlaDashboardCommentPage, SlaDashboardDescription, SlaDashboardIssue } from '@/domain/SlaDashboard'

export const slaDashboardApi = {
  getIssues: async (): Promise<SlaDashboardIssue[]> => {
    const response = await client.get<SlaDashboardIssue[]>('/sla-dashboard/issues')
    return response.data
  },
  getDescription: async (issueKey: string, reportId: number, signal?: CancellationSignal): Promise<SlaDashboardDescription> => {
    const key = encodeURIComponent(issueKey)
    const response = await client.get<SlaDashboardDescription>(`/sla-dashboard/issues/${key}/description`, {
      params: { report_id: reportId },
      signal,
    })
    return response.data
  },
  getDescriptionImage: async (
    issueKey: string,
    attachmentId: string,
    reportId: number,
    signal?: CancellationSignal,
  ): Promise<BinaryContent> => {
    const key = encodeURIComponent(issueKey)
    const attachment = encodeURIComponent(attachmentId)
    const response = await client.get<Blob>(`/sla-dashboard/issues/${key}/description/images/${attachment}`, {
      params: { report_id: reportId },
      responseType: 'blob',
      signal,
    })
    return createBinaryContent(response.data)
  },
  getComments: async (issueKey: string, offset = 0, limit = 5, reportId?: number): Promise<SlaDashboardCommentPage> => {
    const key = encodeURIComponent(issueKey)
    const response = await client.get<SlaDashboardCommentPage>(
      `/sla-dashboard/issues/${key}/comments`,
      { params: { offset, limit, ...(reportId === undefined ? {} : { report_id: reportId }) } },
    )
    return response.data
  },
  getCommentImage: async (
    issueKey: string,
    commentId: string,
    attachmentId: string,
    reportId?: number,
  ): Promise<BinaryContent> => {
    const key = encodeURIComponent(issueKey)
    const comment = encodeURIComponent(commentId)
    const attachment = encodeURIComponent(attachmentId)
    const response = await client.get<Blob>(
      `/sla-dashboard/issues/${key}/comments/${comment}/images/${attachment}`,
      { responseType: 'blob', ...(reportId === undefined ? {} : { params: { report_id: reportId } }) },
    )
    return createBinaryContent(response.data)
  },
}
