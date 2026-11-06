// frontend/src/domain/SoftwareCve.ts
import type { CveCoverage, CveFilters } from '@/domain/Cve'

export interface SoftwareTarget {
  id: string
  label: string
  coverage: string
  available: boolean
}

export interface SoftwareSelection {
  target: string
  version: string
}

export interface SoftwareRelease {
  version: string
  series: string
  label: string
  issued_at: string | null
  supported?: boolean | null
}

export interface SoftwareReleases extends CveCoverage {
  versions: SoftwareRelease[]
}

export type SoftwareCveRequest = SoftwareSelection & CveFilters
