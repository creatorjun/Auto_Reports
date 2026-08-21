// frontend/src/presentation/hooks/useSlaDashboard.ts
import { useQuery } from '@tanstack/react-query'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { SlaDashboardComment, SlaDashboardIssue } from '@/domain/SlaDashboard'

export function useSlaDashboardIssues() {
  const { slaDashboard } = useApplicationServices()
  return useQuery<SlaDashboardIssue[]>({
    queryKey: QUERY_KEYS.slaDashboardIssues(),
    queryFn: slaDashboard.getIssues,
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
    refetchIntervalInBackground: false,
  })
}

export function useSlaIssueComments(issueKey: string, enabled: boolean) {
  const { slaDashboard } = useApplicationServices()
  return useQuery<SlaDashboardComment[]>({
    queryKey: QUERY_KEYS.slaDashboardComments(issueKey),
    queryFn: () => slaDashboard.getComments(issueKey),
    enabled,
    staleTime: 1000 * 60 * 2,
  })
}
