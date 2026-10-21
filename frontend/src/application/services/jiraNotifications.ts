// frontend/src/application/services/jiraNotifications.ts
import type { JiraNotification, JiraNotificationPage } from '@/domain/JiraNotification'

export function jiraNotificationItems(pages: JiraNotificationPage[]): JiraNotification[] {
  if (pages.some((page) => page.connection_status !== 'connected')) return []
  const items = new Map<string, JiraNotification>()
  for (const page of pages) for (const item of page.items) if (!items.has(item.id)) items.set(item.id, item)
  return [...items.values()]
}

export function jiraNotificationReadKey(item: Pick<JiraNotification, 'id' | 'group_id'>): string {
  return JSON.stringify([item.group_id, item.id])
}

export function applyJiraNotificationReads(page: JiraNotificationPage, confirmed: ReadonlySet<string>): JiraNotificationPage {
  return { ...page, items: page.items.map((item) => !item.is_read && confirmed.has(jiraNotificationReadKey(item)) ? { ...item, is_read: true } : item) }
}

export function safeJiraNotificationUrl(value: string | null): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}
