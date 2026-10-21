// frontend/src/presentation/hooks/useJiraNotifications.ts
import { useEffect, useRef, useState } from 'react'
import { useInfiniteQuery, useQueryClient, type InfiniteData } from '@tanstack/react-query'
import { canViewJiraNotifications } from '@/domain/Auth'
import type { JiraNotification, JiraNotificationCategory, JiraNotificationPage } from '@/domain/JiraNotification'
import { applyJiraNotificationReads, jiraNotificationItems, jiraNotificationReadKey } from '@/application/services/jiraNotifications'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { useMe } from './useAuth'

export const JIRA_NOTIFICATIONS_QUERY_KEY = ['jira-notifications'] as const

export function useJiraNotifications(category: JiraNotificationCategory) {
  const { jiraNotifications } = useApplicationServices()
  const accessToken = useAuthStore((state) => state.accessToken)
  const me = useMe()
  const allowed = !!accessToken && !me.isError && canViewJiraNotifications(me.data)
  const queryClient = useQueryClient()
  const refreshing = useRef(false)
  const active = useRef(true)
  const readRequests = useRef(new Map<string, AbortController>())
  const confirmedReads = useRef(new Set<string>())
  const [reading, setReading] = useState<ReadonlySet<string>>(new Set())
  const [readErrors, setReadErrors] = useState<Record<string, string>>({})
  const [readReconnect, setReadReconnect] = useState(false)
  useEffect(() => {
    active.current = true
    setReading(new Set())
    setReadErrors({})
    setReadReconnect(false)
    return () => {
      active.current = false
      for (const controller of readRequests.current.values()) controller.abort()
      readRequests.current.clear()
      confirmedReads.current.clear()
    }
  }, [accessToken])
  const queryKey = [...JIRA_NOTIFICATIONS_QUERY_KEY, accessToken, category]
  const query = useInfiniteQuery({
    queryKey,
    queryFn: async ({ signal, pageParam }) => {
      const page = await jiraNotifications.getNotifications({ category, ...(pageParam ? { cursor: pageParam } : {}) }, signal)
      return applyJiraNotificationReads(page, confirmedReads.current)
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last, _pages, _lastParam, allParams) => last.connection_status === 'connected' && last.next_cursor && !allParams.includes(last.next_cursor) ? last.next_cursor : undefined,
    enabled: allowed,
    staleTime: 0,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  })
  const reconnectRequired = allowed && (readReconnect || (!query.isError && !!query.data?.pages.some((page) => page.connection_status === 'reconnect_required')))
  const visible = allowed && !query.isError && !reconnectRequired
  const refresh = async () => {
    if (!allowed || query.isFetching || refreshing.current) return
    refreshing.current = true
    confirmedReads.current.clear()
    try {
      await queryClient.resetQueries({ queryKey, exact: true })
    } finally {
      refreshing.current = false
    }
  }
  const loadMore = () => {
    if (visible && query.hasNextPage && !query.isFetching) void query.fetchNextPage({ cancelRefetch: false })
  }
  const markRead = async (item: JiraNotification) => {
    const key = jiraNotificationReadKey(item)
    if (!visible || !active.current || !accessToken || useAuthStore.getState().accessToken !== accessToken || item.is_read || !item.group_id || readRequests.current.has(key) || confirmedReads.current.has(key)) return
    const controller = new AbortController()
    readRequests.current.set(key, controller)
    setReading(new Set(readRequests.current.keys()))
    setReadErrors((current) => { const next = { ...current }; delete next[key]; return next })
    const currentSession = () => active.current && !controller.signal.aborted && useAuthStore.getState().accessToken === accessToken && readRequests.current.get(key) === controller
    try {
      const response = await jiraNotifications.markRead({ notification_id: item.id, group_id: item.group_id, category: item.category }, controller.signal)
      if (!currentSession()) return
      if (response.connection_status === 'reconnect_required') {
        setReadReconnect(true)
        return
      }
      if (response.connection_status !== 'connected' || response.is_read !== true || response.notification_id !== item.id || response.group_id !== item.group_id) throw new Error('Notification read was not confirmed')
      confirmedReads.current.add(key)
      queryClient.setQueriesData<InfiniteData<JiraNotificationPage>>({ queryKey: [...JIRA_NOTIFICATIONS_QUERY_KEY, accessToken] }, (data) => data ? { ...data, pages: data.pages.map((page) => applyJiraNotificationReads(page, confirmedReads.current)) } : data)
    } catch {
      if (currentSession()) setReadErrors((current) => ({ ...current, [key]: '읽음 처리에 실패했습니다. 다시 시도해 주세요.' }))
    } finally {
      if (readRequests.current.get(key) === controller) {
        readRequests.current.delete(key)
        if (active.current && useAuthStore.getState().accessToken === accessToken) setReading(new Set(readRequests.current.keys()))
      }
    }
  }
  return {
    allowed,
    items: visible ? jiraNotificationItems(query.data?.pages ?? []) : [],
    reconnectRequired,
    isError: allowed && query.isError,
    error: allowed ? query.error : null,
    isPending: allowed && query.isPending,
    isFetching: allowed && query.isFetching,
    hasMore: visible && query.hasNextPage,
    refresh,
    loadMore,
    markRead,
    isMarkingRead: (item: JiraNotification) => reading.has(jiraNotificationReadKey(item)),
    readError: (item: JiraNotification) => item.is_read ? null : readErrors[jiraNotificationReadKey(item)] ?? null,
  }
}
