// frontend/src/domain/DashboardExport.ts
export type DashboardExportFormat = 'pdf' | 'xlsx'

export interface DashboardExportTableData {
  headers: string[]
  rows: (string | number | null)[][]
}

export interface DashboardPdfCell {
  text: string
  value?: string | number | null
  fillColor?: string
  link?: string
}

export interface DashboardPdfMetricsBlock {
  kind: 'metrics'
  items: { label: string; value: string }[]
}

export interface DashboardPdfTextBlock {
  kind: 'text'
  title?: string
  paragraphs: string[]
  data?: DashboardExportTableData
}

export interface DashboardPdfChartBlock {
  kind: 'chart'
  title: string
  subtitle?: string
  svg: string
  width: number
  height: number
  fullWidth?: boolean
  legend: { label: string; color: string }[]
  data?: DashboardExportTableData
}

export interface DashboardPdfTableBlock {
  kind: 'table'
  title?: string
  headers: string[]
  rows: DashboardPdfCell[][]
  widths?: number[]
}

export type DashboardPdfBlock =
  | DashboardPdfMetricsBlock
  | DashboardPdfTextBlock
  | DashboardPdfChartBlock
  | DashboardPdfTableBlock

export interface DashboardPdfSection {
  title: string
  blocks: DashboardPdfBlock[]
  pageBreakBefore?: boolean
}

export interface DashboardPdfDocument {
  title: string
  period: string
  generatedAt: string
  filters: string[]
  sections: DashboardPdfSection[]
}
