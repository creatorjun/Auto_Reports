// frontend/src/application/services/reportPeriod.ts
import type { ReportPeriod } from '@/domain/ReportPeriod'

export const REPORT_PERIOD_LABELS: Record<ReportPeriod, string> = { week: '주간', month: '월간', year: '연간' }

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
