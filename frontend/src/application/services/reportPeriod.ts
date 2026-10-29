// frontend/src/application/services/reportPeriod.ts
import type { DashboardReportPeriod, DashboardReportRequest, ReportPeriod } from '@/domain/ReportPeriod'

export const REPORT_PERIOD_LABELS: Record<ReportPeriod, string> = { day: '일간', week: '주간', month: '월간', year: '연간' }
export const DASHBOARD_REPORT_PERIOD_LABELS: Record<DashboardReportPeriod, string> = { ...REPORT_PERIOD_LABELS, custom: '기간 지정' }

export function reportToday(now = new Date()): string {
  return new Date(now.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10)
}

export function annualReportDateRange(year: number, today = reportToday()): { start: string; end: string } | null {
  const currentYear = Number(today.slice(0, 4))
  if (!Number.isSafeInteger(year) || year <= 0 || !(year <= currentYear)) return null
  return { start: `${year}-01-01`, end: year === currentYear ? today : `${year}-12-31` }
}

export function reportDateRange(period: ReportPeriod, selectedDate: string): { start: string; end: string } | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(selectedDate)) return null
  const start = new Date(`${selectedDate}T00:00:00Z`)
  if (!Number.isFinite(start.getTime()) || start.toISOString().slice(0, 10) !== selectedDate || start.getUTCFullYear() < 1) return null
  if (period === 'day') return { start: selectedDate, end: selectedDate }
  const end = new Date(start)
  if (period === 'week') {
    start.setUTCDate(start.getUTCDate() - (start.getUTCDay() + 6) % 7)
    end.setTime(start.getTime())
    end.setUTCDate(end.getUTCDate() + 6)
  } else if (period === 'month') {
    start.setUTCDate(1)
    end.setUTCMonth(end.getUTCMonth() + 1, 0)
  } else {
    start.setUTCMonth(0, 1)
    end.setUTCMonth(11, 31)
  }
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) }
}

export function dashboardReportDateRange(request: DashboardReportRequest, today = reportToday()): { start: string; end: string } | null {
  if (request.period !== 'custom') return request.date <= today ? reportDateRange(request.period, request.date) : null
  if (!reportDateRange('day', request.start_date) || !reportDateRange('day', request.end_date)
    || request.start_date > request.end_date || request.end_date > today) return null
  return { start: request.start_date, end: request.end_date }
}
