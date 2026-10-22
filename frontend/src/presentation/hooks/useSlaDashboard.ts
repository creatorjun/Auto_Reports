// frontend/src/presentation/hooks/useSlaDashboard.ts
import { useQuery } from '@tanstack/react-query'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { SlaDashboardIssue } from '@/domain/SlaDashboard'
import { useIssueComments, useIssueDescription } from './useIssueContent'

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

export function useSlaIssueComments(issueKey: string, enabled: boolean, reportId?: number) {
  return useIssueComments(issueKey, enabled, reportId)
}

export function useSlaIssueDescription(issueKey: string, reportId: number) {
  return useIssueDescription(issueKey, reportId)
}
