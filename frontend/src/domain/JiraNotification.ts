// frontend/src/domain/JiraNotification.ts
export type JiraNotificationCategory = 'all' | 'direct' | 'watching'

export interface JiraNotification {
  id: string
  group_id: string
  title: string
  message: string
  url: string | null
  actor: string | null
  created_at: string
  category: 'direct' | 'watching'
  is_read: boolean
  group_size: number
}

export interface JiraNotificationPage {
  connection_status: 'connected' | 'reconnect_required'
  items: JiraNotification[]
  next_cursor: string | null
}

export interface JiraNotificationRequest {
  category: JiraNotificationCategory
  cursor?: string
  unread_only?: boolean
}

export interface JiraNotificationReadRequest {
  notification_id: string
  group_id: string
  category: 'direct' | 'watching'
}

export interface JiraNotificationReadResult {
  connection_status: 'connected' | 'reconnect_required'
  notification_id: string
  group_id: string
  is_read: boolean
}

export interface JiraNotificationReadAllRequest {
  category: JiraNotificationCategory
}

export interface JiraNotificationReadAllResult {
  connection_status: 'connected' | 'reconnect_required'
  category: JiraNotificationCategory
  is_read: boolean
}
