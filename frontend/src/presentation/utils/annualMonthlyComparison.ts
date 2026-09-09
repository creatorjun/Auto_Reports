// frontend/src/presentation/utils/annualMonthlyComparison.ts
import type { MonthlyCountEntry } from '@/domain/Dashboard'

export interface AnnualMonthlyComparisonEntry {
  month: string
  monthNumber: number
  created: number | null
  resolved: number | null
}

export function buildAnnualMonthlyComparison(
  created: MonthlyCountEntry[],
  resolved: MonthlyCountEntry[],
  year: number,
  periodEnd: string,
): AnnualMonthlyComparisonEntry[] {
  const end = /^(\d{4})-(\d{2})-\d{2}/.exec(periodEnd)
  const endYear = end ? Number(end[1]) : year
  const endMonth = end ? Number(end[2]) : 12
  const lastMonth = endYear < year ? 0 : endYear > year ? 12 : Math.min(12, Math.max(0, endMonth))
  const rows = new Map<number, AnnualMonthlyComparisonEntry>()

  for (const [key, entries] of [['created', created], ['resolved', resolved]] as const) {
    for (const entry of entries) {
      if (entry.year !== year || !Number.isInteger(entry.month_num) || entry.month_num < 1 || entry.month_num > lastMonth) continue
      const row = rows.get(entry.month_num) ?? {
        month: `${entry.month_num}월`,
        monthNumber: entry.month_num,
        created: null,
        resolved: null,
      }
      row[key] = Number.isFinite(entry.count) && entry.count >= 0 ? entry.count : null
      rows.set(entry.month_num, row)
    }
  }

  return [...rows.values()].sort((left, right) => left.monthNumber - right.monthNumber)
}
