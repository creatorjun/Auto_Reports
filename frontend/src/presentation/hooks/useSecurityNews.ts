// frontend/src/presentation/hooks/useSecurityNews.ts
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export const SECURITY_NEWS_QUERY_KEY = ['security-news'] as const

export function useSecurityNews() {
  const { securityNews } = useApplicationServices()
  const queryClient = useQueryClient()
  const [now, setNow] = useState(Date.now)
  const refreshPending = useRef(false)
  const query = useQuery({
    queryKey: SECURITY_NEWS_QUERY_KEY,
    queryFn: ({ signal }) => securityNews.getSnapshot(signal),
    staleTime: 30000,
    refetchInterval: (state) => state.state.data?.refreshing ? 2000 : 60000,
    refetchOnWindowFocus: true,
  })
  const mutation = useMutation({
    mutationFn: securityNews.refresh,
    onSuccess: (snapshot) => queryClient.setQueryData(SECURITY_NEWS_QUERY_KEY, snapshot),
    onSettled: () => { refreshPending.current = false },
  })
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const serverRetryAfterSeconds = Math.max(0, query.data?.retry_after_seconds ?? 0)
  const retryAfterSeconds = Math.min(serverRetryAfterSeconds, Math.max(0, Math.ceil((query.dataUpdatedAt + serverRetryAfterSeconds * 1000 - now) / 1000)))
  const refreshing = mutation.isPending || !!query.data?.refreshing
  const canRefresh = !refreshing && !query.isFetching && retryAfterSeconds === 0
  const refresh = () => {
    if (!canRefresh || refreshPending.current) return
    refreshPending.current = true
    mutation.mutate()
  }
  return { ...query, refresh, refreshing, canRefresh, retryAfterSeconds, refreshError: mutation.error, now }
}
