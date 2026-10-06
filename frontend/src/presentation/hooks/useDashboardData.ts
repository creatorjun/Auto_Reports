// frontend/src/presentation/hooks/useDashboardData.ts
import { useMemo } from 'react'
import {
  buildFilteredDashboardData,
  resolveDashboardFilterContract,
} from '@/application/services/dashboardData'
import type { Semester } from '@/domain/Dashboard'
import type { ReportDetail } from '@/domain/Report'

export function useDashboardData(
  report: ReportDetail,
  selectedTypes: ReadonlySet<string> | null = null,
  selectedSemester: Semester | null = null,
  selectedStatuses: ReadonlySet<string> | null = null,
) {
  const filterContract = useMemo(() => resolveDashboardFilterContract(report), [report])
  return useMemo(
    () => buildFilteredDashboardData(report, selectedTypes, selectedSemester, selectedStatuses, filterContract),
    [report, selectedTypes, selectedSemester, selectedStatuses, filterContract],
  )
}
