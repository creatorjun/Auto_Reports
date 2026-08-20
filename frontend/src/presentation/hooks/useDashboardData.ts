// frontend/src/presentation/hooks/useDashboardData.ts
import { useMemo } from 'react'
import type {
  CreatedIssue,
  DataRequestIssue,
  IncompleteIssue,
  MonthlyCountEntry,
  MonthlyEntry,
  ResolvedIssue,
  ResultPendingIssue,
  ReviewIssue,
  SlaDelayIssue,
  ViolationEntry,
  WorkTypeOpenWidget,
} from '@/domain/Dashboard'
import type { ReportDetail } from '@/domain/Report'
import type { RecentIssue } from '@/domain/Issue'
import { WIDGET_ID } from '@/domain/WidgetId'

interface SlaMetData {
  initial_response_violations?: number
  resolution_violations?: number
  violation_distribution?: ViolationEntry[]
}

interface SlaDelayData {
  by_status?: Record<string, number>
  by_status_details?: Record<string, SlaDelayIssue[]>
}

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

interface CreatedVsResolvedData {
  created: number
  resolved: number
  created_details: CreatedIssue[]
  resolved_details: ResolvedIssue[]
}

const WORK_TYPE_DEFINITIONS = [
  { key: 'support', label: '지원 요청', jiraType: '서비스 요청' },
  { key: 'improvement', label: '개선 요청', jiraType: '개선' },
  { key: 'incident', label: '인시던트 보고', jiraType: '인시던트' },
  { key: 'cve', label: 'CVE', jiraType: 'CVE' },
] as const

function getData<T>(widget: { data: Record<string, unknown> | null } | undefined): T | null {
  return (widget?.data ?? null) as T | null
}

function getInclusiveDayCount(start: string, end: string): number {
  const startTime = Date.parse(`${start}T00:00:00Z`)
  const endTime = Date.parse(`${end}T00:00:00Z`)
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime < startTime) return 0
  return Math.floor((endTime - startTime) / 86_400_000) + 1
}

export function useDashboardData(report: ReportDetail) {
  const w = report.widgets

  const weekly = useMemo(() => {
    const w3Data = getData<CreatedVsResolvedData>(w[WIDGET_ID.CREATED_VS_RESOLVED])
    return {
      w3Created: w3Data?.created ?? 0,
      w3Resolved: w3Data?.resolved ?? 0,
      weeklyCreated: w3Data?.created_details ?? [],
      weeklyResolved: w3Data?.resolved_details ?? [],
      dateRange: report.week_start && report.week_end ? { start: report.week_start, end: report.week_end } : undefined,
      rangeDays: getInclusiveDayCount(report.week_start, report.week_end),
    }
  }, [w[WIDGET_ID.CREATED_VS_RESOLVED], report.week_start, report.week_end])

  const slaMonthly = useMemo(() => {
    const w10Data = getData<{ monthly: MonthlyEntry[] }>(w[WIDGET_ID.SLA_INITIAL_RESPONSE])
    const w11Data = getData<{ monthly: MonthlyEntry[] }>(w[WIDGET_ID.SLA_RESOLUTION_MONTHLY])
    const w10Monthly = w10Data?.monthly ?? []
    const w11Monthly = w11Data?.monthly ?? []
    return {
      w10Monthly,
      w11Monthly,
      hasW10: w10Monthly.some((e) => e.total > 0),
      hasW11: w11Monthly.some((e) => e.total > 0),
    }
  }, [w[WIDGET_ID.SLA_INITIAL_RESPONSE], w[WIDGET_ID.SLA_RESOLUTION_MONTHLY]])

  const monthlyCount = useMemo(() => {
    const w8Data = getData<{ monthly: MonthlyCountEntry[] }>(w[WIDGET_ID.MONTHLY_CREATED])
    const w9Data = getData<{ monthly: MonthlyCountEntry[] }>(w[WIDGET_ID.MONTHLY_RESOLVED])
    const w8Monthly = w8Data?.monthly ?? []
    const w9Monthly = w9Data?.monthly ?? []
    return {
      w8Monthly,
      w9Monthly,
      hasW8: w8Monthly.some((e) => e.count > 0),
      hasW9: w9Monthly.some((e) => e.count > 0),
    }
  }, [w[WIDGET_ID.MONTHLY_CREATED], w[WIDGET_ID.MONTHLY_RESOLVED]])

  const slaDonut = useMemo(() => {
    const w12Data = getData<SlaMetData>(w[WIDGET_ID.SLA_MET_VS_VIOLATED])
    return {
      w12Total: w[WIDGET_ID.SLA_MET_VS_VIOLATED]?.total ?? 0,
      w12Distribution: w12Data?.violation_distribution ?? [],
    }
  }, [w[WIDGET_ID.SLA_MET_VS_VIOLATED]])

  const slaDelay = useMemo(() => {
    const w13Data = getData<SlaDelayData>(w[WIDGET_ID.SLA_DELAY_REASON])
    return {
      w13ByStatus: w13Data?.by_status ?? {},
      w13ByStatusDetails: w13Data?.by_status_details ?? {},
    }
  }, [w[WIDGET_ID.SLA_DELAY_REASON]])

  const resolutionByType = useMemo(() => {
    const w14Data = getData<{ by_type: Record<string, ResolutionTypeEntry> }>(w[WIDGET_ID.AVG_RESOLUTION_TYPE])
    return w14Data?.by_type ?? {}
  }, [w[WIDGET_ID.AVG_RESOLUTION_TYPE]])

  const recentAndIncomplete = useMemo(() => {
    const w7Data = getData<{ issue_details: RecentIssue[] }>(w[WIDGET_ID.RECENT_ISSUES])
    const recentIssues = (w7Data?.issue_details ?? []).map((i) => ({
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
  }, [w[WIDGET_ID.RECENT_ISSUES]])

  const workTypeOpen = useMemo<WorkTypeOpenWidget[]>(() => (
    WORK_TYPE_DEFINITIONS.map(({ key, label, jiraType }) => {
      const issues = recentAndIncomplete.incompleteIssues.filter((issue) => issue.type === jiraType)
      return {
        key,
        label,
        count: issues.length,
        issues,
      }
    })
  ), [recentAndIncomplete])

  const statusIssues = useMemo(() => {
    const w4Data = getData<{ issue_details: ReviewIssue[] }>(w[WIDGET_ID.ISSUE_REVIEW])
    const w5Data = getData<{ issue_details: DataRequestIssue[] }>(w[WIDGET_ID.DATA_REQUEST])
    const w6Data = getData<{ issue_details: ResultPendingIssue[] }>(w[WIDGET_ID.RESULT_PENDING])
    return {
      reviewIssues: w4Data?.issue_details ?? [],
      dataRequestIssues: w5Data?.issue_details ?? [],
      resultPendingIssues: w6Data?.issue_details ?? [],
    }
  }, [w[WIDGET_ID.ISSUE_REVIEW], w[WIDGET_ID.DATA_REQUEST], w[WIDGET_ID.RESULT_PENDING]])

  return { weekly, workTypeOpen, slaMonthly, monthlyCount, slaDonut, slaDelay, resolutionByType, recentAndIncomplete, statusIssues }
}
