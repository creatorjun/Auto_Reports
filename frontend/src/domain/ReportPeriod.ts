// frontend/src/domain/ReportPeriod.ts
export type ReportPeriod = 'week' | 'month' | 'year'

export interface PeriodReportRequest {
  period: ReportPeriod
  date: string
}
