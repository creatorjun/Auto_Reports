// frontend/src/domain/SolutionPackages.ts
export type SolutionProduct = 'eyeCloudSIM' | 'eyeCloudXoar' | 'eyeCloudAI'

export interface SolutionPackage {
  id: string
  name: string
  version: string
  category: string
  evidence: string
  cve_ids: string[] | null
}

export interface SolutionPackageInventory {
  packages: SolutionPackage[]
}
