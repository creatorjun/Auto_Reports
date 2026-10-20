// frontend/src/domain/SecurityNews.ts
export type SecurityNewsKind = 'cve' | 'advisory' | 'news'
export type SecuritySeverity = 'critical' | 'high' | 'medium' | 'low' | 'unknown'
export type SecurityNewsLanguage = 'ko' | 'original'

export interface SecurityNewsItem {
  id: string
  source_id: string
  kind: SecurityNewsKind
  title: string
  summary: string
  title_ko?: string | null
  summary_ko?: string | null
  url: string
  published_at: string | null
  updated_at: string | null
  cve_ids: string[]
  severity: SecuritySeverity
  cvss_score: number | null
  cvss_version: string | null
  known_exploited: boolean
  vendor: string | null
  product: string | null
  due_date: string | null
}

export interface SecurityNewsSource {
  id: string
  name: string
  homepage: string
  kind: SecurityNewsKind
  status: 'ok' | 'stale' | 'error' | 'pending'
  count: number
  last_success_at: string | null
  error: string | null
  warning?: string | null
}

export interface SecurityNewsSnapshot {
  items: SecurityNewsItem[]
  sources: SecurityNewsSource[]
  initialized: boolean
  refreshing: boolean
  refreshed_at: string | null
  next_refresh_at: string | null
  retry_after_seconds: number
  refresh_interval_seconds: number
  translation?: SecurityNewsTranslation
}

export interface SecurityNewsTranslation {
  enabled: boolean
  translating: boolean
  translated_count: number
  pending_count: number
  message: string | null
}

export interface SecurityNewsFilters {
  kind: SecurityNewsKind | 'all'
  search: string
  source: string
  severity: SecuritySeverity | 'all'
  exploitedOnly: boolean
  days: 7 | 30 | 'all'
  sort: 'newest' | 'severity'
}
