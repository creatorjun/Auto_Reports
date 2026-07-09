// frontend/src/infrastructure/hooks/useReport.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { TriggerParams } from '@/domain/Job'

export const useLatestReport = () =>
  useQuery<ReportDetail | null>({
    queryKey: ['reports', 'latest'],
    queryFn: reportApi.getLatest,
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 10,
    refetchIntervalInBackground: false,
  })

export const useReportById = (id: number) =>
  useQuery<ReportDetail>({
    queryKey: ['reports', id],
    queryFn: () => reportApi.getById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  })

export const useAllReports = (page = 0, pageSize = 20) =>
  useQuery<ReportSummary[]>({
    queryKey: ['reports', 'list', page, pageSize],
    queryFn: () => reportApi.getAll(pageSize, page * pageSize),
    placeholderData: (prev) => prev,
    staleTime: 1000 * 60 * 2,
  })

export const useDeleteReport = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => reportApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

interface RefreshCallbacks {
  onComplete: (reportId: number | null) => void
  onError:    (message: string) => void
  onTimeout:  () => void
}

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS  = 180000

export const useRefreshReport = (callbacks?: RefreshCallbacks) => {
  const queryClient = useQueryClient()
  let timerRef: ReturnType<typeof setInterval> | null = null
  let elapsed = 0

  const stopPolling = () => {
    if (timerRef !== null) {
      clearInterval(timerRef)
      timerRef = null
    }
    elapsed = 0
  }

  const startPolling = (jobId: string) => {
    elapsed = 0
    timerRef = setInterval(async () => {
      elapsed += POLL_INTERVAL_MS
      if (elapsed >= POLL_TIMEOUT_MS) {
        stopPolling()
        callbacks?.onTimeout()
        return
      }
      try {
        const status = await reportApi.getJobStatus(jobId)
        if (status.status === 'done') {
          stopPolling()
          queryClient.invalidateQueries({ queryKey: ['reports'] })
          callbacks?.onComplete(status.report_id)
        } else if (status.status === 'error') {
          stopPolling()
          callbacks?.onError(status.error ?? '알 수 없는 오류')
        }
      } catch {
        stopPolling()
        callbacks?.onError('상태 확인 중 오류가 발생했습니다.')
      }
    }, POLL_INTERVAL_MS)
  }

  return useMutation({
    mutationFn: (params: TriggerParams) => reportApi.trigger(params),
    onSuccess: (data) => startPolling(data.job_id),
  })
}
