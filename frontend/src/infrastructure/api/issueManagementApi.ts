// frontend/src/infrastructure/api/issueManagementApi.ts
import client from './client'
import { createBinaryContent } from './binaryContent'
import type { BinaryContent, CancellationSignal } from '@/application/ports/ApplicationServices'
import type { IssueManagementSnapshot } from '@/domain/IssueManagement'
import type { SlaDashboardCommentPage, SlaDashboardDescription } from '@/domain/SlaDashboard'

export const issueManagementApi = {
  getIssues: async (): Promise<IssueManagementSnapshot> => {
    const response = await client.get<IssueManagementSnapshot>('/issue-management/issues')
    return response.data
  },
  getDescription: async (issueKey: string, signal?: CancellationSignal): Promise<SlaDashboardDescription> => {
    const response = await client.get<SlaDashboardDescription>(`/issue-management/issues/${encodeURIComponent(issueKey)}/description`, { signal })
    return response.data
  },
  getDescriptionImage: async (issueKey: string, attachmentId: string, signal?: CancellationSignal): Promise<BinaryContent> => {
    const response = await client.get<Blob>(`/issue-management/issues/${encodeURIComponent(issueKey)}/description/images/${encodeURIComponent(attachmentId)}`, { responseType: 'blob', signal })
    return createBinaryContent(response.data)
  },
  getComments: async (issueKey: string, offset = 0, limit = 5): Promise<SlaDashboardCommentPage> => {
    const response = await client.get<SlaDashboardCommentPage>(`/issue-management/issues/${encodeURIComponent(issueKey)}/comments`, { params: { offset, limit } })
    return response.data
  },
  getCommentImage: async (issueKey: string, commentId: string, attachmentId: string): Promise<BinaryContent> => {
    const response = await client.get<Blob>(`/issue-management/issues/${encodeURIComponent(issueKey)}/comments/${encodeURIComponent(commentId)}/images/${encodeURIComponent(attachmentId)}`, { responseType: 'blob' })
    return createBinaryContent(response.data)
  },
}
