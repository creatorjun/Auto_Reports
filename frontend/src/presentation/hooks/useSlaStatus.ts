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
  const refreshing = query.isFetching || mutation.isPending
  const refresh = () => {
    if (refreshing || refreshPending.current) return
    refreshPending.current = true
    const controller = new AbortController()
    refreshController.current = controller
    mutation.mutate(controller)
  }
  return { ...query, refresh, refreshing, refreshError: mutation.error }
}
