// frontend/src/domain/Cve.ts
import type { SecuritySeverity } from '@/domain/SecurityNews'

export type CveCoverageStatus = 'pending' | 'ready' | 'partial' | 'stale' | 'error'

export interface CveCoverage {
  status: CveCoverageStatus
  refreshing: boolean
  coverage_note: string | null
  sources: {
    id: string
    label: string
    url: string
    status: CveCoverageStatus
    refreshed_at: string | null
    note: string | null
  }[]
}

export interface CveFilters {
  severity: SecuritySeverity | 'all'
  search: string
  page: number
  page_size: number
}

export interface CveFix {
  advisory_id: string
  advisory_url: string
  title: string | null
  issued_at: string | null
  fixed_version: string | null
  affected_from?: string | null
  affected_from_inclusive?: boolean
  affected_through?: string | null
  affected_through_inclusive?: boolean
  affected_version?: string | null
  component?: string | null
  cvss_score?: number | null
  channel?: string | null
  series?: string | null
}

export interface CveFinding {
  cve_id: string
  severity: SecuritySeverity
  summary: string | null
  fixes: CveFix[]
}

export interface CveResults extends CveCoverage {
  total: number | null
  page: number
  page_size: number
  severity_counts: Record<SecuritySeverity, number>
  items: CveFinding[]
}
