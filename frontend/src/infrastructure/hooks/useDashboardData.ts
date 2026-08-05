// frontend/src/infrastructure/hooks/useDashboardData.ts
import { useMemo } from 'react'
import type { ReportDetail } from '@/domain/Report'
import type { RecentIssue } from '@/domain/Issue'
import type { ViolationEntry } from '@/presentation/components/charts/SlaDonutChart'
import type { SlaDelayIssue } from '@/presentation/components/charts/ReasonPieChart'
import type { MonthlyEntry } from '@/presentation/components/charts/SlaMonthlyLineChart'
import type { MonthlyCountEntry } from '@/presentation/components/charts/MonthlyCountChart'
import type { CreatedIssue } from '@/presentation/components/tables/WeeklyCreatedModal'
import type { ResolvedIssue } from '@/presentation/components/tables/WeeklyResolvedModal'
import type { ReviewIssue } from '@/presentation/components/tables/IssueReviewModal'
import type { DataRequestIssue } from '@/presentation/components/tables/DataRequestModal'
import type { ResultPendingIssue } from '@/presentation/components/tables/ResultPendingModal'
import type { IncompleteIssue } from '@/presentation/components/tables/IncompleteIssueModal'

interface W9Data {
  initial_response_violations?: number
  resolution_violations?: number
  violation_distribution?: ViolationEntry[]
}

interface W10Data {
  by_status?: Record<string, number>
  by_status_details?: Record<string, SlaDelayIssue[]>
}

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

function getData<T>(widget: { data: Record<string, unknown> | null } | undefined): T | null {
  return (widget?.data ?? null) as T | null
}

export function useDashboardData(report: ReportDetail) {
  const w = report.widgets

  const weekly = useMemo(() => {
    const w3Data = getData<{ created: number; resolved: number; created_details: CreatedIssue[]; resolved_details: ResolvedIssue[] }>(w.w3)
    return {
      w3Created: w3Data?.created ?? 0,
      w3Resolved: w3Data?.resolved ?? 0,
      weeklyCreated: w3Data?.created_details ?? [],
      weeklyResolved: w3Data?.resolved_details ?? [],
      dateRange: report.week_start && report.week_end ? { start: report.week_start, end: report.week_end } : undefined,
    }
  }, [w.w3, report.week_start, report.week_end])

  const slaMonthly = useMemo(() => {
    const w7Data = getData<{ monthly: MonthlyEntry[] }>(w.w7)
    const w8Data = getData<{ monthly: MonthlyEntry[] }>(w.w8)
    const w7Monthly = w7Data?.monthly ?? []
    const w8Monthly = w8Data?.monthly ?? []
    return {
      w7Monthly,
      w8Monthly,
      hasW7: w7Monthly.some((e) => e.total > 0),
      hasW8: w8Monthly.some((e) => e.total > 0),
    }
  }, [w.w7, w.w8])

  const monthlyCount = useMemo(() => {
    const w13Data = getData<{ monthly: MonthlyCountEntry[] }>(w.w13)
    const w14Data = getData<{ monthly: MonthlyCountEntry[] }>(w.w14)
    const w13Monthly = w13Data?.monthly ?? []
    const w14Monthly = w14Data?.monthly ?? []
    return {
      w13Monthly,
      w14Monthly,
      hasW13: w13Monthly.some((e) => e.count > 0),
      hasW14: w14Monthly.some((e) => e.count > 0),
    }
  }, [w.w13, w.w14])

  const slaDonut = useMemo(() => {
    const w9Data = getData<W9Data>(w.w9)
    return {
      w9Total: w.w9?.total ?? 0,
      w9Distribution: w9Data?.violation_distribution ?? [],
    }
  }, [w.w9])

  const slaDelay = useMemo(() => {
    const w10Data = getData<W10Data>(w.w10)
    return {
      w10ByStatus: w10Data?.by_status ?? {},
      w10ByStatusDetails: w10Data?.by_status_details ?? {},
    }
  }, [w.w10])

  const resolutionByType = useMemo(() => {
    const w11Data = getData<{ by_type: Record<string, ResolutionTypeEntry> }>(w.w11)
    return w11Data?.by_type ?? {}
  }, [w.w11])

  const recentAndIncomplete = useMemo(() => {
    const w12Data = getData<{ issue_details: RecentIssue[] }>(w.w12)
    const recentIssues = (w12Data?.issue_details ?? []).map((i) => ({
      ...i,
      reporter: i.reporter ?? '미지정',
      tac_team: i.tac_team ?? '미지정',
    }))
    const incompleteIssues: IncompleteIssue[] = recentIssues.map((i) => ({
      key: i.key,
      summary: i.summary,
      type: i.type,
      status: i.status,
      created: i.created,
      elapsed_days: i.elapsed_days,
    }))
    return { recentIssues, incompleteIssues, incompleteTotal: incompleteIssues.length }
  }, [w.w12])

  const statusIssues = useMemo(() => {
    const w4Data = getData<{ issue_details: ReviewIssue[] }>(w.w4)
    const w5Data = getData<{ issue_details: DataRequestIssue[] }>(w.w5)
    const w6Data = getData<{ issue_details: ResultPendingIssue[] }>(w.w6)
    return {
      reviewIssues: w4Data?.issue_details ?? [],
      dataRequestIssues: w5Data?.issue_details ?? [],
      resultPendingIssues: w6Data?.issue_details ?? [],
    }
  }, [w.w4, w.w5, w.w6])

  return { weekly, slaMonthly, monthlyCount, slaDonut, slaDelay, resolutionByType, recentAndIncomplete, statusIssues }
}
