// frontend/src/presentation/hooks/useJiraNotifications.ts
import { useRef } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { canViewJiraNotifications } from '@/domain/Auth'
import type { JiraNotificationCategory } from '@/domain/JiraNotification'
import { jiraNotificationItems } from '@/application/services/jiraNotifications'
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
  const queryKey = [...JIRA_NOTIFICATIONS_QUERY_KEY, accessToken, category]
  const query = useInfiniteQuery({
    queryKey,
    queryFn: ({ signal, pageParam }) => jiraNotifications.getNotifications({ category, ...(pageParam ? { cursor: pageParam } : {}) }, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (last, _pages, _lastParam, allParams) => last.connection_status === 'connected' && last.next_cursor && !allParams.includes(last.next_cursor) ? last.next_cursor : undefined,
    enabled: allowed,
    staleTime: 0,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  })
  const reconnectRequired = allowed && !query.isError && !!query.data?.pages.some((page) => page.connection_status === 'reconnect_required')
  const visible = allowed && !query.isError && !reconnectRequired
  const refresh = async () => {
    if (!allowed || query.isFetching || refreshing.current) return
    refreshing.current = true
    try {
      await queryClient.resetQueries({ queryKey, exact: true })
    } finally {
      refreshing.current = false
    }
  }
  const loadMore = () => {
    if (visible && query.hasNextPage && !query.isFetching) void query.fetchNextPage({ cancelRefetch: false })
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
  }
}
