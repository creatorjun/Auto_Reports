// frontend/src/presentation/hooks/useRedeployments.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

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
    onMutate: async () => { await client.cancelQueries({ queryKey: latestKey }) },
    onSuccess: async (report) => {
      await client.cancelQueries({ queryKey: latestKey })
      client.setQueryData(latestKey, report)
    },
    retry: false,
  })
}
