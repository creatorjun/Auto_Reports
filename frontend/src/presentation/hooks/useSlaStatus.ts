// frontend/src/presentation/hooks/useSlaStatus.ts
import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export const SLA_STATUS_QUERY_KEY = ['sla-status'] as const

export function useSlaStatus() {
  const { slaStatus } = useApplicationServices()
  const queryClient = useQueryClient()
  const refreshController = useRef<AbortController | null>(null)
  const refreshPending = useRef(false)
  const query = useQuery({
    queryKey: SLA_STATUS_QUERY_KEY,
    queryFn: ({ signal }) => slaStatus.getSnapshot(false, signal),
    staleTime: 60_000,
    refetchOnMount: 'always',
    refetchInterval: (state) => state.state.data?.refresh_in_progress ? 2000 : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: false,
  })
  const mutation = useMutation({
    mutationFn: async (controller: AbortController) => {
      await queryClient.cancelQueries({ queryKey: SLA_STATUS_QUERY_KEY })
      if (controller.signal.aborted) throw new Error('SLA 조회가 취소되었습니다.')
      return slaStatus.getSnapshot(true, controller.signal)
    },
    onSuccess: (snapshot, controller) => {
      if (!controller.signal.aborted) queryClient.setQueryData(SLA_STATUS_QUERY_KEY, snapshot)
    },
    onSettled: () => { refreshController.current = null; refreshPending.current = false },
    retry: false,
  })
  useEffect(() => () => refreshController.current?.abort(), [])
  const refreshing = query.isFetching || mutation.isPending || (query.data?.refresh_in_progress === true && !query.isError)
  const refresh = () => {
    if (refreshing || refreshPending.current) return
    refreshPending.current = true
    const controller = new AbortController()
    refreshController.current = controller
    mutation.mutate(controller)
  }
  const mutationError = mutation.error && query.dataUpdatedAt <= mutation.submittedAt ? mutation.error : null
  return { ...query, refresh, refreshing, refreshError: mutationError ?? query.data?.refresh_error ?? null }
}
