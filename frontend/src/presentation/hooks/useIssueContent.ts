// frontend/src/presentation/hooks/useIssueContent.ts
import { useMemo } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import type { IssueContentGateway } from '@/application/ports/ApplicationServices'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export type IssueContentSource = 'issue-management'

export function useIssueContentGateway(reportId?: number, source?: IssueContentSource): IssueContentGateway {
  const { slaDashboard, issueManagement } = useApplicationServices()
  return useMemo(() => source === 'issue-management' ? issueManagement : {
    getDescription: (key, signal) => slaDashboard.getDescription(key, reportId, signal),
    getDescriptionImage: (key, attachment, signal) => slaDashboard.getDescriptionImage(key, attachment, reportId, signal),
    getComments: (key, offset, limit) => slaDashboard.getComments(key, offset, limit, reportId),
    getCommentImage: (key, comment, attachment) => slaDashboard.getCommentImage(key, comment, attachment, reportId),
  }, [source, reportId, slaDashboard, issueManagement])
}

export function useIssueDescription(issueKey: string, reportId?: number, source?: IssueContentSource) {
  const gateway = useIssueContentGateway(reportId, source)
  return useQuery({
    queryKey: source === 'issue-management' ? QUERY_KEYS.managedIssueDescription(issueKey) : QUERY_KEYS.slaDashboardDescription(issueKey, reportId),
    queryFn: ({ signal }) => gateway.getDescription(issueKey, signal),
    staleTime: 1000 * 60 * 2,
    retry: false,
  })
}

export function useIssueComments(issueKey: string, enabled: boolean, reportId?: number, source?: IssueContentSource) {
  const gateway = useIssueContentGateway(reportId, source)
  return useInfiniteQuery({
    queryKey: source === 'issue-management' ? QUERY_KEYS.managedIssueComments(issueKey) : QUERY_KEYS.slaDashboardComments(issueKey, reportId),
    queryFn: ({ pageParam }) => gateway.getComments(issueKey, 0, pageParam),
    initialPageParam: 5,
    getNextPageParam: (lastPage) => lastPage.next_offset === null ? undefined : lastPage.next_offset + 5,
    maxPages: 1,
    select: (data) => data.pages[data.pages.length - 1]?.comments ?? [],
    enabled,
    staleTime: 1000 * 60 * 2,
  })
}
