// frontend/src/presentation/hooks/useCLevelReport.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { CLevelCommentInput, CLevelPeriod, CLevelReport } from '@/domain/CLevelReport'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export const cLevelQueryKey = (period: CLevelPeriod, date: string, snapshotId?: number) => ['c-level-report', period, date, snapshotId ?? 'preview'] as const

export function useCLevelReport(period: CLevelPeriod, date: string, snapshotId?: number) {
  const { cLevelReport } = useApplicationServices()
  const queryClient = useQueryClient()
  const queryKey = cLevelQueryKey(period, date, snapshotId)
  const report = useQuery({
    queryKey,
    queryFn: ({ signal }) => snapshotId === undefined ? cLevelReport.getReport(period, date, false, signal) : cLevelReport.getSnapshot(snapshotId, signal),
    retry: false,
    staleTime: snapshotId === undefined ? 5 * 60_000 : Infinity,
    refetchOnWindowFocus: false,
  })
  const refresh = useMutation({
    mutationFn: (request: { period: CLevelPeriod; date: string; queryKey: ReturnType<typeof cLevelQueryKey> }) => cLevelReport.getReport(request.period, request.date, true),
    onSuccess: (data, request) => queryClient.setQueryData(request.queryKey, data),
  })
  const comment = useMutation({
    mutationFn: ({ key, input, token }: { key: string; input: CLevelCommentInput; token: string | null | undefined; queryKey: ReturnType<typeof cLevelQueryKey> }) => {
      if (!token) return Promise.reject(new Error('저장된 보고서는 수정할 수 없습니다.'))
      return cLevelReport.saveComment(key, token, input)
    },
    onSuccess: (saved, variables) => queryClient.setQueryData<CLevelReport>(variables.queryKey, (current) => current ? { ...current, comments: { ...current.comments, [variables.key]: saved } } : current),
  })
  const snapshot = useMutation({
    mutationFn: () => {
      const token = report.data?.report_token
      if (!token) return Promise.reject(new Error('조회한 보고서가 없습니다. 새로고침 후 다시 저장해 주세요.'))
      return cLevelReport.saveSnapshot(token, `집중(특별) 관리 보고 · ${report.data?.start_date} ~ ${report.data?.end_date}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['c-level-snapshots'] }),
  })
  return {
    report,
    refresh: { ...refresh, mutate: () => refresh.mutate({ period, date, queryKey }) },
    comment: { ...comment, mutateAsync: ({ key, input }: { key: string; input: CLevelCommentInput }) => comment.mutateAsync({ key, input, token: report.data?.report_token, queryKey }) },
    snapshot,
  }
}

export function useCLevelSnapshots(page = 0, pageSize = 20) {
  const { cLevelReport } = useApplicationServices()
  return useQuery({ queryKey: ['c-level-snapshots', page, pageSize], queryFn: () => cLevelReport.getSnapshots(pageSize, page * pageSize), retry: false })
}
