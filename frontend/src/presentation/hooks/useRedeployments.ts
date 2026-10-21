// frontend/src/presentation/hooks/useRedeployments.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

const latestKey = ['redeployments', 'latest'] as const

export function useRedeployments() {
  const { redeployments } = useApplicationServices()
  return useQuery({
    queryKey: latestKey, queryFn: ({ signal }) => redeployments.getLatest(signal),
    staleTime: 0, refetchOnMount: 'always', refetchInterval: 60_000, retry: 1,
  })
}

export function useRefreshRedeployments() {
  const { redeployments } = useApplicationServices()
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => redeployments.generate(),
    onMutate: async () => {
      const sessionVersion = useAuthStore.getState().sessionVersion
      await client.cancelQueries({ queryKey: latestKey })
      if (sessionVersion !== useAuthStore.getState().sessionVersion) throw new Error('Session changed')
      return sessionVersion
    },
    onSuccess: async (report, _, sessionVersion) => {
      if (sessionVersion !== useAuthStore.getState().sessionVersion) return
      await client.cancelQueries({ queryKey: latestKey })
      if (sessionVersion !== useAuthStore.getState().sessionVersion) return
      client.setQueryData(latestKey, report)
    },
    retry: false,
  })
}
