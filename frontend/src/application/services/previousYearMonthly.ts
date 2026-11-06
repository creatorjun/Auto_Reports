// frontend/src/application/services/previousYearMonthly.ts
import { filterMonthlyCounts, filterSlaMonthly } from '@/application/services/dashboardData'
import { observedPeriodEnd } from '@/application/services/reportPeriod'
import type { MonthlyCountEntry, MonthlyEntry, RedeploymentMonthlyEntry, Semester } from '@/domain/Dashboard'
import { isDashboardMonthInSemester, isLicenseIssueType } from '@/domain/DashboardIssueTypePolicy'
import type { ReportDetail } from '@/domain/Report'
import { WIDGET_ID, type WidgetId } from '@/domain/WidgetId'

export interface PreviousYearMonthly {
  created: MonthlyCountEntry[]
  resolved: MonthlyCountEntry[]
  slaInitial: MonthlyEntry[]
  slaResolution: MonthlyEntry[]
  redeployments: RedeploymentMonthlyEntry[]
}

type Month = { year: number; month_num: number }
const monthlyWidgets = [
  WIDGET_ID.MONTHLY_CREATED, WIDGET_ID.MONTHLY_RESOLVED, WIDGET_ID.SLA_INITIAL_RESPONSE,
  WIDGET_ID.SLA_RESOLUTION_MONTHLY, WIDGET_ID.REDEPLOYMENT_ANALYTICS,
]

function monthRows<T extends Month>(report: ReportDetail, widgetId: WidgetId): T[] {
  const rows = report.widgets[widgetId]?.data?.monthly
  return Array.isArray(rows) ? rows : []
}

export function monthlyComparisonYears(report: ReportDetail): number[] {
  const years = new Set<number>()
  for (const id of monthlyWidgets) {
    for (const month of monthRows(report, id)) {
      if (Number.isInteger(month.year) && month.year > 1) years.add(month.year - 1)
    }
  }
  return [...years].sort()
}

function coveredRows<T extends Month>(report: ReportDetail, id: WidgetId, semester: Semester | null): T[] {
  const start = report.week_start.slice(0, 7)
  const end = observedPeriodEnd(report).slice(0, 7)
  return monthRows<T>(report, id).filter((row) => {
    const month = `${row.year}-${String(row.month_num).padStart(2, '0')}`
    return row.year === report.report_year && row.month_num >= 1 && row.month_num <= 12
      && month >= start && month <= end && (!semester || isDashboardMonthInSemester(semester, row.month_num))
  })
}

type Bucket = number | { total: number; met: number }
const bucketTotal = (value: Bucket) => typeof value === 'number' ? value : value.total

function comparableRows<T extends MonthlyCountEntry | MonthlyEntry>(
  rows: T[],
  types: ReadonlySet<string> | null,
  statuses: ReadonlySet<string> | null,
  controlled: ReadonlySet<string>,
  filter: (rows: T[], types: ReadonlySet<string> | null, controlled: ReadonlySet<string>, statuses: ReadonlySet<string> | null, semester: Semester | null, year: number) => T[],
): T[] {
  if (types === null && statuses === null) return rows
  return rows.flatMap((row) => {
    const total = 'count' in row ? row.count : row.total
    if (total === 0) return [row]
    const byType = row.by_type
    if (statuses === null && types && byType) {
      const other = row.always_included == null ? 0 : bucketTotal(row.always_included)
      const typeTotal = Object.values<Bucket>(byType).reduce<number>((sum, value) => sum + bucketTotal(value), other)
      const excludedTypeInOther = other > 0 && [...controlled].some((type) => !types.has(type) && !(type in byType))
      if (typeTotal === total && !excludedTypeInOther) return filter([row], types, controlled, null, null, row.year)
    }
    const byStatus = row.by_status_type
    if (byStatus) {
      const statusTotal = Object.values(byStatus).flatMap((counts) => Object.values<Bucket>(counts))
        .reduce<number>((sum, value) => sum + bucketTotal(value), 0)
      if (statusTotal === total) {
        return filter([row], types, controlled, statuses ?? new Set(Object.keys(byStatus)), null, row.year)
      }
    }
    return []
  })
}

export function previousYearMonthly(
  reports: readonly ReportDetail[],
  types: ReadonlySet<string> | null,
  statuses: ReadonlySet<string> | null,
  semester: Semester | null,
  controlledTypes: readonly string[],
): PreviousYearMonthly {
  const result: PreviousYearMonthly = { created: [], resolved: [], slaInitial: [], slaResolution: [], redeployments: [] }
  const controlled = new Set(controlledTypes)
  for (const report of reports) {
    if (report.scope !== 'annual') continue
    const counts = (id: WidgetId) => comparableRows(coveredRows<MonthlyCountEntry>(report, id, semester), types, statuses, controlled, filterMonthlyCounts)
    const sla = (id: WidgetId) => comparableRows(coveredRows<MonthlyEntry>(report, id, semester), types, statuses, controlled, filterSlaMonthly)
    result.created.push(...counts(WIDGET_ID.MONTHLY_CREATED))
    result.resolved.push(...counts(WIDGET_ID.MONTHLY_RESOLVED))
    result.slaInitial.push(...sla(WIDGET_ID.SLA_INITIAL_RESPONSE))
    result.slaResolution.push(...sla(WIDGET_ID.SLA_RESOLUTION_MONTHLY))
    if (report.widgets[WIDGET_ID.REDEPLOYMENT_ANALYTICS]?.data?.classification_complete === true) {
      for (const row of coveredRows<RedeploymentMonthlyEntry>(report, WIDGET_ID.REDEPLOYMENT_ANALYTICS, null)) {
        const byType = Object.fromEntries(Object.entries(row.by_type).filter(([type]) => !isLicenseIssueType(type)))
        result.redeployments.push({ ...row, by_type: byType, total: Object.values(byType).reduce((sum, count) => sum + count, 0) })
      }
    }
  }
  return result
}
