// frontend/src/domain/SolutionPackages.ts
import type { CveCoverage } from '@/domain/Cve'

export type SolutionProduct = 'eyeCloudSIM' | 'eyeCloudXoar' | 'eyeCloudAI'

export interface SolutionPackage {
  id: string
  name: string
  version: string
  category: string
  evidence: string
  cve_ids: string[] | null
  cve_basis?: 'inventory' | 'advisory'
}

export interface SolutionPackageInventory {
  packages: SolutionPackage[]
  coverage?: CveCoverage | null
}
