// frontend/src/presentation/hooks/useReport.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { isRefreshableAnnualReport, REPORT_REFRESH_INTERVAL_MS } from '@/presentation/config/annualReports'

export const useLatestReport = (enabled = true) => {
  const { reports } = useApplicationServices()
  return useQuery<ReportDetail | null>({
    queryKey: QUERY_KEYS.latestReport(),
    queryFn: reports.getLatest,
    enabled,
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
