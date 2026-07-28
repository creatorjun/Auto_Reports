// frontend/src/domain/Site.ts
export type SiteStatus = 'active' | 'inactive' | 'expired' | 'maintenance'

export interface SiteSummary {
  id: string
  site_name: string
  customer_name?: string
  status?: SiteStatus
  contract_end_date?: string
}

export interface ContactInfo {
  name?: string
  phone?: string
  email?: string
}

export interface Credential {
  username: string
  password: string
}

export interface AccessCredentials {
  cli?: Credential
  web?: Credential
  db?: Credential
  vpn?: Credential
  note?: string
}

export interface DeploymentNode {
  id?: number
  hostname?: string
  role?: string
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

export interface PatchHistory {
  id?: number
  issue_link?: string
  patch_date?: string
  patch_file_link?: string
  patch_type?: string
  applied_by?: string
  result_status?: string
  rollback_date?: string
  note?: string
}

export interface VisitHistory {
  id?: number
  visit_date?: string
  visitor?: string
  visit_type?: string
  visit_summary?: string
  next_visit_scheduled?: string
}

export interface SiteDetail {
  id: string
  site_name: string
  maintenance_company?: string
  customer_info?: ContactInfo
  maintenance_info?: ContactInfo
  contract_start_date?: string
  contract_end_date?: string
  contract_type?: string
  status?: string
  created_at: string
  updated_at: string
  nodes: DeploymentNode[]
  solution_package?: SolutionPackage
  patch_histories: PatchHistory[]
  visit_histories: VisitHistory[]
  access_credentials?: AccessCredentials
}

export interface SiteCreatePayload {
  id: string
  site_name: string
  maintenance_company?: string
  customer_info?: ContactInfo
  maintenance_info?: ContactInfo
  contract_start_date?: string
  contract_end_date?: string
  contract_type?: string
  status?: SiteStatus
  nodes: []
  patch_histories: []
  visit_histories: []
  access_credentials?: AccessCredentials
}
