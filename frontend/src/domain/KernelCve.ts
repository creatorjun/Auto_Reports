// frontend/src/domain/KernelCve.ts
import type { CveCoverage, CveCoverageStatus, CveFilters, CveFinding, CveFix, CveResults } from '@/domain/Cve'

export interface KernelTarget {
  id: string
  label: string
  available: boolean
  packages: string[]
  architectures: string[]
  coverage: string
}

export interface KernelBuild {
  target: string
  package: string
  architecture: string
}

export interface KernelSelection extends KernelBuild {
  version: string
}

export interface KernelReleases extends CveCoverage {
  versions: string[]
}

export type KernelCveRequest = KernelSelection & CveFilters

export interface KernelFix extends CveFix {
  fixed_version: string
  package: string
  architecture: string
}

export interface KernelFinding extends CveFinding {
  fixes: KernelFix[]
}

export interface KernelCveResults extends CveResults {
  items: KernelFinding[]
}

export type UpstreamKernelRequest = Pick<KernelCveRequest, 'target' | 'search' | 'page' | 'page_size'>

export interface UpstreamKernelResults {
  items: { cve_id: string; title: string; published_at: string | null; url: string }[]
  total: number | null
  page: number
  page_size: number
  status: CveCoverageStatus
  refreshing: boolean
  as_of: string | null
}
