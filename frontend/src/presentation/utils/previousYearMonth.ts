// frontend/src/presentation/utils/previousYearMonth.ts
export { observedPeriodEnd } from '@/application/services/reportPeriod'

type CalendarMonth = { year: number; month_num: number }

export function previousYearMonth<T extends CalendarMonth>(month: CalendarMonth, history: T[]) {
  return history.find((entry) => entry.year === month.year - 1 && entry.month_num === month.month_num)
}

export function throughReportMonth<T extends CalendarMonth>(rows: T[], periodEnd: string) {
  const lastMonth = periodEnd.slice(0, 7)
  return rows.filter((entry) => !entry.year || !entry.month_num || `${entry.year}-${String(entry.month_num).padStart(2, '0')}` <= lastMonth)
}
