// frontend/src/infrastructure/api/issueManagementApi.ts
import client from './client'
import type { IssueManagementSnapshot } from '@/domain/IssueManagement'

export const issueManagementApi = {
  getIssues: async (): Promise<IssueManagementSnapshot> => {
    const response = await client.get<IssueManagementSnapshot>('/issue-management/issues')
    return response.data
  },
}
