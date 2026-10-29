// frontend/src/domain/ReportPeriod.ts
export type ReportPeriod = 'day' | 'week' | 'month' | 'year'

export interface PeriodReportRequest {
  period: ReportPeriod
  date: string
}

export interface CustomReportRequest {
  period: 'custom'
  start_date: string
  end_date: string
}

export type DashboardReportPeriod = ReportPeriod | 'custom'
export type DashboardReportRequest = PeriodReportRequest | CustomReportRequest
