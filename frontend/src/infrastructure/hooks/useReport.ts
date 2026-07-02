import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import type { ReportDetail, ReportSummary } from '@/domain/Report'

export const useLatestReport = () =>
  useQuery<ReportDetail | null>({
    queryKey: ['reports', 'latest'],
    queryFn: reportApi.getLatest,
    refetchInterval: 1000 * 60 * 10
  })

export const useReportById = (id: number) =>
  useQuery<ReportDetail>({
    queryKey: ['reports', id],
    queryFn: () => reportApi.getById(id),
    enabled: !!id
  })

export const useAllReports = () =>
  useQuery<ReportSummary[]>({
    queryKey: ['reports'],
    queryFn: () => reportApi.getAll()
  })

export const useDeleteReport = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => reportApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    }
  })
}
