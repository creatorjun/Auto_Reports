// frontend/src/presentation/hooks/useReport.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RequestError } from '@/application/errors/RequestError'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { TriggerParams } from '@/domain/Job'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { isRefreshableAnnualReport, REPORT_REFRESH_INTERVAL_MS } from '@/presentation/config/annualReports'
import { useJobStream } from '@/presentation/hooks/useJobStream'

export const useLatestReport = () => {
  const { reports } = useApplicationServices()
  return useQuery<ReportDetail | null>({
    queryKey: QUERY_KEYS.latestReport(),
    queryFn: reports.getLatest,
    staleTime: REPORT_REFRESH_INTERVAL_MS,
    refetchInterval: REPORT_REFRESH_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })
}

export const useAnnualReport = (year: number) => {
  const { reports } = useApplicationServices()
  const refreshable = isRefreshableAnnualReport(year)
  return useQuery<ReportDetail>({
    queryKey: QUERY_KEYS.annualReport(year),
    queryFn: () => reports.getAnnual(year),
    enabled: Number.isInteger(year) && year > 0,
    staleTime: refreshable ? REPORT_REFRESH_INTERVAL_MS : Infinity,
    refetchInterval: refreshable ? REPORT_REFRESH_INTERVAL_MS : false,
    refetchIntervalInBackground: false,
    refetchOnMount: refreshable,
    refetchOnWindowFocus: refreshable,
    refetchOnReconnect: refreshable,
  })
}

export const useReportById = (id: number) => {
  const { reports } = useApplicationServices()
  return useQuery<ReportDetail>({
    queryKey: QUERY_KEYS.reportById(id),
    queryFn: () => reports.getById(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  })
}

export const useAllReports = (page = 0, pageSize = 20) => {
  const { reports } = useApplicationServices()
  return useQuery<ReportSummary[]>({
    queryKey: QUERY_KEYS.allReports(page, pageSize),
    queryFn: () => reports.getAll(pageSize, page * pageSize),
    placeholderData: (prev) => prev,
    staleTime: 1000 * 60 * 2,
  })
}

export const useDeleteReport = () => {
  const { reports } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => reports.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allReportsBase() })
    },
  })
}

interface RefreshCallbacks {
  onComplete: (reportId: number | null) => void
  onError:    (message: string) => void
  onTimeout:  () => void
}

const REFRESH_TIMEOUT_MS = 180_000

function resolveTriggerError(err: unknown): string {
  if (err instanceof RequestError) {
    const { status, detail } = err
    if (status === 409) {
      return typeof detail === 'string'
        ? detail
        : '이미 실행 중인 작업이 있습니다. 잠시 후 다시 시도하세요.'
    }
    if (status === 401) return '인증이 만료되었습니다. 다시 로그인해 주세요.'
    if (status === 422) return '요청 형식이 올바르지 않습니다.'
    if (status != null && status >= 500) return `서버 오류가 발생했습니다. (${status})`
    if (detail) return String(detail)
  }
  return '보고서 갱신 요청에 실패했습니다.'
}

export const useRefreshReport = (callbacks?: RefreshCallbacks) => {
  const { reports } = useApplicationServices()
  const queryClient = useQueryClient()
  const { start, stop } = useJobStream({
    onComplete: async (reportId) => {
      await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allReportsBase() })
      callbacks?.onComplete(reportId)
    },
    onError: (message) => callbacks?.onError(message),
    onTransportError: (error) => callbacks?.onError(resolveTriggerError(error)),
    onTimeout: () => callbacks?.onTimeout(),
  }, REFRESH_TIMEOUT_MS)

  return useMutation({
    mutationFn: (params?: TriggerParams | void) => reports.trigger(params ?? undefined),
    onSuccess: (data) => start(data.job_id),
    onError: (err) => {
      stop()
      callbacks?.onError(resolveTriggerError(err))
    },
  })
}
