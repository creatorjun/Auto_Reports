// frontend/src/presentation/hooks/useSlaDashboard.ts
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { SlaDashboardIssue } from '@/domain/SlaDashboard'

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
  return useInfiniteQuery({
    queryKey: QUERY_KEYS.slaDashboardComments(issueKey),
    queryFn: ({ pageParam }) => slaDashboard.getComments(issueKey, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
    select: (data) => {
      const seen = new Set<string>()
      return data.pages.flatMap((page) => page.comments).filter((comment) => {
        if (seen.has(comment.id)) return false
        seen.add(comment.id)
        return true
      })
    },
    enabled,
    staleTime: 1000 * 60 * 2,
  })
}
