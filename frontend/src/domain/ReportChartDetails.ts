// frontend/src/domain/ReportChartDetails.ts
export interface ChartIssue {
  key: string
  summary: string
  type: string
  status?: string | null
  created?: string | null
  resolved?: string | null
  month?: string | null
  cause?: string | null
  assignee?: string | null
  partners?: string[]
  priority?: string | null
  sla_met?: boolean | null
  elapsed_hours?: number | null
}

export interface ChartIssuesRequest {
  chart: 'sla_initial' | 'sla_resolution' | 'resolution_type' | 'redeployment'
  month?: number
  issue_type?: string
  semester?: 'h1' | 'h2'
  partner?: string
  cause?: string
  assignee?: string
  filter_types?: boolean
  selected_types?: string[]
  filter_statuses?: boolean
  selected_statuses?: string[]
  sla_status?: 'all' | 'met' | 'violated'
}

export interface ChartIssuesResult {
  issues: ChartIssue[]
  snapshot_count: number | null
  current_count: number
  source_total: number
  source_total_exact: boolean
  collection_limit: number | null
  truncated: boolean
  queried_at: string
  snapshot_at: string
  source: 'current_jira'
}
