export interface AiAnalysis {
  summary: string
  risks: string[]
  recommendations: string[]
  sentiment: 'good' | 'warning' | 'critical'
}

export interface WidgetResult {
  name: string
  total: number
  jql: string
  breakdown: Record<string, unknown>
}

export interface ReportSummary {
  id: number
  week_start: string
  week_end: string
  report_date: string
  created_at: string
  sentiment: 'good' | 'warning' | 'critical' | null
}

export interface ReportDetail extends ReportSummary {
  widgets: Record<string, WidgetResult>
  ai_analysis: AiAnalysis | null
}
