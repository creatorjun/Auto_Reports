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
  Semester,
  SlaDelayIssue,
  ViolationEntry,
  WorkTypeOpenWidget,
} from '@/domain/Dashboard'
import type { ReportDetail } from '@/domain/Report'
import type { RecentIssue } from '@/domain/Issue'
import { WIDGET_ID } from '@/domain/WidgetId'

interface TypeCountData {
  issue_types?: string[]
  by_type?: Record<string, number>
  always_included?: number | null
}

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

interface ResolutionTypeData {
  by_type: Record<string, ResolutionTypeEntry>
  by_semester?: Partial<Record<Semester, Record<string, ResolutionTypeEntry>>>
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

function getReportYear(report: ReportDetail): number {
  const year = Number.parseInt(report.week_end?.slice(0, 4) ?? '', 10)
  return Number.isFinite(year) ? year : new Date().getFullYear()
}

function semesterIncludesMonth(semester: Semester, month: number): boolean {
  return semester === 'h1' ? month >= 1 && month <= 6 : month >= 7 && month <= 12
}

function dateIsInSemester(value: string, year: number, semester: Semester): boolean {
  const dateYear = Number.parseInt(value.slice(0, 4), 10)
  const month = Number.parseInt(value.slice(5, 7), 10)
  return dateYear === year && semesterIncludesMonth(semester, month)
}

function includesType(
  issueType: string,
  selectedTypes: ReadonlySet<string> | null,
  controlledTypes: ReadonlySet<string>,
): boolean {
  return selectedTypes === null || !controlledTypes.has(issueType) || selectedTypes.has(issueType)
}

function filterIssues<T extends { type: string }>(
  issues: T[],
  selectedTypes: ReadonlySet<string> | null,
  controlledTypes: ReadonlySet<string>,
  semester: Semester | null = null,
  reportYear: number = 0,
  getDate?: (issue: T) => string,
): T[] {
  return issues.filter((issue) => (
    includesType(issue.type, selectedTypes, controlledTypes)
    && (
      semester === null
      || getDate === undefined
      || dateIsInSemester(getDate(issue), reportYear, semester)
    )
  ))
}

function sumSelectedTypes(
  byType: Record<string, number> | undefined,
  fallback: number,
  selectedTypes: ReadonlySet<string> | null,
  alwaysIncluded: number | null | undefined,
): number {
  if (!byType || selectedTypes === null) return fallback
  return Object.entries(byType).reduce(
    (total, [issueType, count]) => total + (selectedTypes.has(issueType) ? count : 0),
    alwaysIncluded ?? 0,
  )
}

function filterMonthlyCounts(
  monthly: MonthlyCountEntry[],
  selectedTypes: ReadonlySet<string> | null,
  semester: Semester | null,
  reportYear: number,
): MonthlyCountEntry[] {
  return monthly
    .filter((entry) => (
      semester === null
      || (
        entry.year === reportYear
        && semesterIncludesMonth(semester, entry.month_num)
      )
    ))
    .map((entry) => ({
      ...entry,
      count: sumSelectedTypes(
        entry.by_type,
        entry.count,
        selectedTypes,
        entry.always_included,
      ),
    }))
}

function filterSlaMonthly(
  monthly: MonthlyEntry[],
  selectedTypes: ReadonlySet<string> | null,
  semester: Semester | null,
  reportYear: number,
): MonthlyEntry[] {
  return monthly.filter((entry) => (
    semester === null
    || (
      entry.year === reportYear
      && semesterIncludesMonth(semester, entry.month_num)
    )
  )).map((entry) => {
    if (!entry.by_type) return entry
    const stats = [
      ...(entry.always_included ? [entry.always_included] : []),
      ...Object.entries(entry.by_type)
        .filter(([issueType]) => selectedTypes === null || selectedTypes.has(issueType))
        .map(([, value]) => value),
    ]
    const met = stats.reduce((total, value) => total + value.met, 0)
    const total = stats.reduce((sum, value) => sum + value.total, 0)
    return {
      ...entry,
      met,
      total,
      rate: total > 0 ? Math.round((met / total) * 1000) / 10 : 0,
    }
  })
}

function resolveFilterContract(report: ReportDetail) {
  const data = getData<TypeCountData>(report.widgets[WIDGET_ID.YEARLY_CREATED])
  const monthlyData = getData<{ monthly: MonthlyCountEntry[] }>(
    report.widgets[WIDGET_ID.MONTHLY_CREATED],
  )
  const issueTypes = data?.issue_types?.filter(Boolean) ?? []
  const reportYear = getReportYear(report)
  const availableMonths = new Set(
    (monthlyData?.monthly ?? [])
      .filter((entry) => entry.year === reportYear)
      .map((entry) => entry.month_num),
  )
  return {
    issueTypes,
    reportYear,
    supportsIssueTypeFiltering: (
      issueTypes.length > 0
      && data?.by_type !== undefined
      && typeof data.always_included === 'number'
    ),
    supportsSemesterFiltering: Array.from(
      { length: 12 },
      (_, index) => index + 1,
    ).every((month) => availableMonths.has(month)),
  }
}

export function buildDashboardData(
  report: ReportDetail,
  requestedTypes: ReadonlySet<string> | null = null,
  requestedSemester: Semester | null = null,
) {
  const w = report.widgets
  const filterContract = resolveFilterContract(report)
  const selectedTypes = filterContract.supportsIssueTypeFiltering ? requestedTypes : null
  const selectedSemester = filterContract.supportsSemesterFiltering ? requestedSemester : null
  const controlledTypes = new Set(filterContract.issueTypes)
  const { reportYear } = filterContract
  const semesterLabel = selectedSemester === 'h1'
    ? `${reportYear}년 상반기`
    : selectedSemester === 'h2'
      ? `${reportYear}년 하반기`
      : `${reportYear}년 전체`
  const filter = {
    ...filterContract,
    selectedSemester,
    semesterLabel,
  }

  const w8Data = getData<{ monthly: MonthlyCountEntry[] }>(w[WIDGET_ID.MONTHLY_CREATED])
  const w9Data = getData<{ monthly: MonthlyCountEntry[] }>(w[WIDGET_ID.MONTHLY_RESOLVED])
  const w8Monthly = filterMonthlyCounts(
    w8Data?.monthly ?? [],
    selectedTypes,
    selectedSemester,
    reportYear,
  )
  const w9Monthly = filterMonthlyCounts(
    w9Data?.monthly ?? [],
    selectedTypes,
    selectedSemester,
    reportYear,
  )
  const monthlyCount = {
    w8Monthly,
    w9Monthly,
    hasW8: w8Monthly.some((entry) => entry.count > 0),
    hasW9: w9Monthly.some((entry) => entry.count > 0),
  }

  const yearlyCreatedData = getData<TypeCountData>(w[WIDGET_ID.YEARLY_CREATED])
  const yearlyResolvedData = getData<TypeCountData>(w[WIDGET_ID.YEARLY_RESOLVED])
  const yearly = {
    w1YearlyCreated: selectedSemester === null
      ? sumSelectedTypes(
          yearlyCreatedData?.by_type,
          w[WIDGET_ID.YEARLY_CREATED]?.total ?? 0,
          selectedTypes,
          yearlyCreatedData?.always_included,
        )
      : w8Monthly.reduce((total, entry) => total + entry.count, 0),
    w2YearlyResolved: selectedSemester === null
      ? sumSelectedTypes(
          yearlyResolvedData?.by_type,
          w[WIDGET_ID.YEARLY_RESOLVED]?.total ?? 0,
          selectedTypes,
          yearlyResolvedData?.always_included,
        )
      : w9Monthly.reduce((total, entry) => total + entry.count, 0),
  }

  const w3Data = getData<CreatedVsResolvedData>(w[WIDGET_ID.CREATED_VS_RESOLVED])
  const weeklyCreated = filterIssues(
    w3Data?.created_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.created,
  )
  const weeklyResolved = filterIssues(
    w3Data?.resolved_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.resolved,
  )
  const weekly = {
    w3Created: weeklyCreated.length,
    w3Resolved: weeklyResolved.length,
    weeklyCreated,
    weeklyResolved,
    dateRange: report.week_start && report.week_end
      ? { start: report.week_start, end: report.week_end }
      : undefined,
    rangeDays: getInclusiveDayCount(report.week_start, report.week_end),
  }

  const w10Data = getData<{ monthly: MonthlyEntry[] }>(w[WIDGET_ID.SLA_INITIAL_RESPONSE])
  const w11Data = getData<{ monthly: MonthlyEntry[] }>(w[WIDGET_ID.SLA_RESOLUTION_MONTHLY])
  const w10Monthly = filterSlaMonthly(
    w10Data?.monthly ?? [],
    selectedTypes,
    selectedSemester,
    reportYear,
  )
  const w11Monthly = filterSlaMonthly(
    w11Data?.monthly ?? [],
    selectedTypes,
    selectedSemester,
    reportYear,
  )
  const slaMonthly = {
    w10Monthly,
    w11Monthly,
    hasW10: w10Monthly.some((entry) => entry.total > 0),
    hasW11: w11Monthly.some((entry) => entry.total > 0),
  }

  const w12Data = getData<SlaMetData>(w[WIDGET_ID.SLA_MET_VS_VIOLATED])
  const rawViolationDistribution = w12Data?.violation_distribution ?? []
  const filteredViolationDistribution = rawViolationDistribution
    .map((entry) => {
      const issueDetails = filterIssues(
        entry.issue_details ?? [],
        selectedTypes,
        controlledTypes,
        selectedSemester,
        reportYear,
        (issue) => issue.created,
      )
      return { ...entry, count: issueDetails.length, issue_details: issueDetails }
    })
    .filter((entry) => entry.count > 0)
  const w12Total = filteredViolationDistribution.reduce((total, entry) => total + entry.count, 0)
  const w12Distribution = filteredViolationDistribution.map((entry) => ({
    ...entry,
    rate: w12Total > 0 ? Math.round((entry.count / w12Total) * 1000) / 10 : 0,
  }))
  const slaDonut = { w12Total, w12Distribution }

  const w13Data = getData<SlaDelayData>(w[WIDGET_ID.SLA_DELAY_REASON])
  const w13ByStatus: Record<string, number> = {}
  const w13ByStatusDetails: Record<string, SlaDelayIssue[]> = {}
  for (const [status, issues] of Object.entries(w13Data?.by_status_details ?? {})) {
    const filteredIssues = filterIssues(
      issues,
      selectedTypes,
      controlledTypes,
      selectedSemester,
      reportYear,
      (issue) => issue.created,
    )
    if (filteredIssues.length === 0) continue
    w13ByStatus[status] = filteredIssues.length
    w13ByStatusDetails[status] = filteredIssues
  }
  const slaDelay = { w13ByStatus, w13ByStatusDetails }

  const w14Data = getData<ResolutionTypeData>(w[WIDGET_ID.AVG_RESOLUTION_TYPE])
  const rawResolutionByType = selectedSemester === null
    ? w14Data?.by_type
    : w14Data?.by_semester?.[selectedSemester]
  const resolutionByType = Object.fromEntries(
    Object.entries(rawResolutionByType ?? {})
      .filter(([issueType]) => includesType(issueType, selectedTypes, controlledTypes)),
  )

  const w7Data = getData<{ issue_details: RecentIssue[] }>(w[WIDGET_ID.RECENT_ISSUES])
  const recentIssues = filterIssues(
    w7Data?.issue_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.created,
  ).map((issue) => ({
    ...issue,
    reporter: issue.reporter ?? '미지정',
    tac_team: issue.tac_team ?? '미지정',
  }))
  const incompleteIssues: IncompleteIssue[] = recentIssues.map((issue) => ({
    key: issue.key,
    summary: issue.summary,
    type: issue.type,
    status: issue.status,
    created: issue.created,
    elapsed_days: issue.elapsed_days,
  }))
  const recentAndIncomplete = {
    recentIssues,
    incompleteIssues,
    incompleteTotal: incompleteIssues.length,
  }

  const workTypeOpen: WorkTypeOpenWidget[] = WORK_TYPE_DEFINITIONS.map(({ key, label, jiraType }) => {
    const issues = incompleteIssues.filter((issue) => issue.type === jiraType)
    return { key, label, count: issues.length, issues }
  })

  const w4Data = getData<{ issue_details: ReviewIssue[] }>(w[WIDGET_ID.ISSUE_REVIEW])
  const w5Data = getData<{ issue_details: DataRequestIssue[] }>(w[WIDGET_ID.DATA_REQUEST])
  const w6Data = getData<{ issue_details: ResultPendingIssue[] }>(w[WIDGET_ID.RESULT_PENDING])
  const reviewIssues = filterIssues(
    w4Data?.issue_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.created,
  )
  const dataRequestIssues = filterIssues(
    w5Data?.issue_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.created,
  )
  const resultPendingIssues = filterIssues(
    w6Data?.issue_details ?? [],
    selectedTypes,
    controlledTypes,
    selectedSemester,
    reportYear,
    (issue) => issue.created,
  )
  const statusIssues = {
    reviewIssues,
    dataRequestIssues,
    resultPendingIssues,
    reviewTotal: reviewIssues.length,
    dataRequestTotal: dataRequestIssues.length,
    resultPendingTotal: resultPendingIssues.length,
  }

  return {
    filter,
    yearly,
    weekly,
    workTypeOpen,
    slaMonthly,
    monthlyCount,
    slaDonut,
    slaDelay,
    resolutionByType,
    recentAndIncomplete,
    statusIssues,
  }
}

export function useDashboardData(
  report: ReportDetail,
  selectedTypes: ReadonlySet<string> | null = null,
  selectedSemester: Semester | null = null,
) {
  return useMemo(
    () => buildDashboardData(report, selectedTypes, selectedSemester),
    [report, selectedTypes, selectedSemester],
  )
}
