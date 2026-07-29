// frontend/src/domain/Site.ts
export type SiteStatus = 'installing' | 'active' | 'inactive' | 'expired' | 'maintenance'

export interface SiteSummary {
  id: number
  site_name: string
  customer_name?: string
  status?: SiteStatus
  contract_end_date?: string
}

export interface ContactInfo {
  name?: string
  phone?: string
  email?: string
  company?: string
}

export interface Credential {
  username: string
  password: string
  ip?: string
  port?: string
}

export interface AccessCredentials {
  cli?: Credential
  web?: Credential
  db?: Credential
  vpn?: Credential
  note?: string
}

export type NodeRole = 'AllInOne' | 'Analyzer' | 'Collector'

export interface DeploymentNode {
  id?: number
  hostname?: string
  role?: NodeRole
  cpu_cores?: number
  cpu_threads?: number
  memory_total_gb?: number
  disk_total_gb?: number
  os_type?: string
  os_version?: string
  ip_address?: string
  disk_free_gb?: number
  disk_updated_at?: string
}

export interface DeploymentNodePayload {
  hostname?: string
  role?: NodeRole
  cpu_cores?: number
  cpu_threads?: number
  memory_total_gb?: number
  disk_total_gb?: number
  os_type?: string
  os_version?: string
  ip_address?: string
  disk_free_gb?: number
  disk_updated_at?: string
}

export interface SolutionPackage {
  id?: number
  version?: string
  installer_filename?: string
  license_capacity_gb?: number
  deployment_type?: string
  license_key?: string
  license_expire_date?: string
  installed_at?: string
  updated_at?: string
}

export interface SolutionPackagePayload {
  version?: string
  installer_filename?: string
  license_capacity_gb?: number
  deployment_type?: string
  license_key?: string
  license_expire_date?: string
  installed_at?: string
}

export interface PatchHistory {
  id?: number
  issue_link?: string
  patch_date?: string
  patch_file_link?: string
  patch_type?: string
  appl