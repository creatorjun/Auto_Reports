// frontend/src/infrastructure/api/jiraNotificationApi.ts
import type { JiraNotificationGateway } from '@/application/ports/ApplicationServices'
import type { JiraNotificationPage, JiraNotificationReadAllResult, JiraNotificationReadResult } from '@/domain/JiraNotification'
import client from './client'

export const jiraNotificationApi: JiraNotificationGateway = {
  getNotifications: async (request, signal) => {
    const response = await client.get<JiraNotificationPage>('/jira/notifications', { params: request, signal })
    return response.data
  },
  markRead: async (request, signal) => {
    const response = await client.post<JiraNotificationReadResult>('/jira/notifications/read', request, { signal })
    return response.data
  },
  markAllRead: async (request, signal) => {
    const response = await client.post<JiraNotificationReadAllResult>('/jira/notifications/read-all', request, { signal })
    return response.data
  },
}
