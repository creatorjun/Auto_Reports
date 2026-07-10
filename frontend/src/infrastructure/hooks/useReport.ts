// frontend/src/infrastructure/hooks/useReport.ts
import { useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
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

function resolveTriggerError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    if (status === 409) return detail ?? '이미 실행 중인 작업이 있습니다. 잠시 후 다시 시도하세요.'
    if (status === 401) return '인증이 만료되었습니다. 다시 로그인해 주세요.'
    if (status === 422) return '요청 형식이 올바르지 않습니다.'
    if (status != null && status >= 500) return `서버 오류가 발생했습니다. (${status})`
    if (detail) return String(detail)
  }
  return '보고서 갱신 요청에 실패했습니다.'
}

export const useRefreshReport = (callbacks?: RefreshCallbacks) => {
  const queryClient = useQueryClient()
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsedRef  = useRef<number>(0)

  const stopPolling = () => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    elapsedRef.current = 0
  }

  const startPolling = (jobId: string) => {
    stopPolling()
    elapsedRef.current = 0
    timerRef.current = setInterval(async () => {
      elapsedRef.current += POLL_INTERVAL_MS
      if (elapsedRef.current >= POLL_TIMEOUT_MS) {
        stopPolling()
        callbacks?.onTimeout()
        return
      }
      try {
        const status = await reportApi.getJobStatus(jobId)
        if (status.status === 'done') {
          stopPolling()
          await queryClient.invalidateQueries({ queryKey: ['reports'] })
          callbacks?.onComplete(status.report_id)
        } else if (status.status === 'error') {
          stopPolling()
          callbacks?.onError(status.error ?? '알 수 없는 오류')
        }
      } catch (err) {
        stopPolling()
        callbacks?.onError(resolveTriggerError(err))
      }
    }, POLL_INTERVAL_MS)
  }

  return useMutation({
    mutationFn: (params: TriggerParams) => reportApi.trigger(params),
    onSuccess: (data) => startPolling(data.job_id),
    onError: (err) => {
      stopPolling()
      callbacks?.onError(resolveTriggerError(err))
    },
  })
}
