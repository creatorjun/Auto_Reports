// frontend/src/domain/CveInventory.ts
import type { SecuritySeverity } from '@/domain/SecurityNews'

export type CveInventoryImpact = 'affected' | 'not_affected' | 'unknown'
export type CveCollectionStatus = 'ok' | 'stale' | 'error' | 'pending' | 'unmapped'

export interface CveInventoryRequest {
  severity: SecuritySeverity | 'all'
  search: string
  ecosystem: string
  impact: CveInventoryImpact | 'all'
  page: number
  page_size: number
  sort: 'severity' | 'newest' | 'package'
}

export interface CveInventoryFinding {
  id: string
  package_id: string
  package_name: string
  ecosystem: string
  inventory_versions: string[]
  product_names: string[]
  categories: string[]
  cve_id: string
  title: string
  affected_versions: string[]
  fixed_versions: string[]
  ranges: { affected: string; fixed: string | null; type: string }[]
  severity: SecuritySeverity
  cvss_score: number | null
  cvss_version: string | null
  references: string[]
  source_ids: string[]
  source: string
  published_at: string | null
  modified_at: string | null
  inventory_impact: CveInventoryImpact
  affected_inventory_versions: string[]
  first_seen_at: string | null
  known_exploited: boolean
  severity_source: string | null
  collection_status: CveCollectionStatus
}

export interface CveInventorySnapshot {
  items: CveInventoryFinding[]
  total: number
  page: number
  page_size: number
  severity_counts: Record<SecuritySeverity, number>
  inventory: {
    dataset_id: string
    snapshot_at: string | null
    product_count: number
    target_count: number
    package_count: number
    runtime_verified: boolean
  }
  coverage: { total: number; ready: number; unmapped: number; ok: number; stale: number; error: number; pending: number }
  ecosystems: string[]
  initialized: boolean
  refreshing: boolean
  refreshed_at: string | null
  next_refresh_at: string | null
  retry_after_seconds: number
  refresh_interval_seconds: number
  progress: { completed: number; total: number }
  error: string | null
}

export interface CveInventoryPackageRequest {
  search: string
  status: CveCollectionStatus | 'all'
  page: number
  page_size: number
}

export interface CveInventoryPackage {
  id: string
  name: string
  ecosystem: string
  versions: string[]
  product_names: string[]
  categories: string[]
  source: string
  mapping_status: string
  mapping_reason: string | null
  status: CveCollectionStatus
  last_success_at: string | null
  last_attempt_at: string | null
  error: string | null
  cve_count: number
}

export interface CveInventoryPackagePage {
  items: CveInventoryPackage[]
  total: number
  page: number
  page_size: number
}
