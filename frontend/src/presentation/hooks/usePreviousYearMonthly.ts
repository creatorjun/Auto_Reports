// frontend/src/presentation/hooks/usePreviousYearMonthly.ts
import { useMemo } from 'react'
import { useQueries, type UseQueryResult } from '@tanstack/react-query'
import { monthlyComparisonYears, previousYearMonthly } from '@/application/services/previousYearMonthly'
import type { Semester } from '@/domain/Dashboard'
import type { ReportDetail } from '@/domain/Report'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export type { PreviousYearMonthly } from '@/application/services/previousYearMonthly'

function combineAnnualReports(queries: UseQueryResult<ReportDetail>[]) {
  return {
    reports: queries.flatMap((query) => query.data ? [query.data] : []),
    isLoading: queries.some((query) => query.isLoading),
  }
}

export function usePreviousYearMonthly(
  report: ReportDetail,
  types: ReadonlySet<string> | null,
  statuses: ReadonlySet<string> | null,
  semester: Semester | null,
  controlledTypes: readonly string[],
  enabled = true,
) {
  const { reports } = useApplicationServices()
  const years = useMemo(() => monthlyComparisonYears(report), [report])
  const history = useQueries({
    queries: enabled ? years.map((year) => ({
      queryKey: QUERY_KEYS.annualReport(year),
      queryFn: () => reports.getAnnual(year),
      staleTime: Infinity,
      retry: false,
      refetchOnWindowFocus: false,
    })) : [],
    combine: combineAnnualReports,
  })
  const values = useMemo(
    () => previousYearMonthly(history.reports, types, statuses, semester, controlledTypes),
    [history.reports, types, statuses, semester, controlledTypes],
  )
  return { ...values, isLoading: history.isLoading }
}
