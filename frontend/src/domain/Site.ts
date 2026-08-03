// frontend/src/domain/Site.ts
export type SiteStatus = 'installing' | 'active' | 'inactive' | 'expired' | 'maintenance'

export type ContractType = '정식라이센스' | '임시라이센스'

export type DeploymentType = '올인원' | '분리구성'

export type NodeRole = 'AllInOne' | 'Analyzer' | 'Collector' | 'Proxy'

export type PatchType = '정기패치' | '긴급패치' | '핫픽스'

export type PatchResultStatus = '성공' | '실패' | '롤백'

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
  deployment_type?: DeploymentType
  license_key?: string
  license_expire_date?: string
  installed_at?: string
  updated_at?: string
}

export interface SolutionPackagePayload {
  version?: string
  installer_filename?: string
  license_capacity_gb?: number
  deployment_type?: DeploymentType
  license_key?: string
  license_expire_date?: string
  installed_at?: string
}

export interface PatchHistory {
  id?: number
  issue_link?: string
  patch_date?: string
  patch_file_link?: string
  patch_type?: PatchType
  applied_by?: string
  result_status?: PatchResultStatus
  rollback_date?: string
  note?: string
}

export interface PatchHistoryPayload {
  patch_date?: string
  patch_type?: PatchType
  applied_by?: string
  result_status?: PatchResultStatus
  issue_link?: string
  patch_file_link?: string
  rollback_date?: string
  note?: string
}

export interface VisitHistory {
  id?: number
  visit_datetime?: string
  engineer_name?: string
  engineer_phone?: string
  request_content?: string
  action_content?: string
}

export interface VisitHistoryPayload {
  visit_datetime?: string
  engineer_name?: string
  engineer_phone?: string
  request_content?: string
  action_content?: string
}

export interface SiteSummary {
  id: number
  site_name: string
  customer_name?: string
  status?: SiteStatus
  contract_end_date?: string
}

export interface SiteDetail {
  id: number
  site_name: string
  maintenance_company?: string
  customer_info?: ContactInfo
  maintenance_info?: ContactInfo
  contract_start_date?: string
  contract_end_date?: string
  contract_type?: ContractType
  status?: SiteStatus
  created_at: string
  updated_at: string
  nodes: DeploymentNode[]
  solution_package?: SolutionPackage
  patch_histories: PatchHistory[]
  visit_histories: VisitHistory[]
  access_credentials?: AccessCredentials
}

export interface SiteCreatePayload {
  site_name: string
  maintenance_company?: string
  customer_info?: ContactInfo
  maintenance_info?: ContactInfo
  contract_start_date?: string
  contract_end_date?: string
  contract_type?: ContractType
  status?: SiteStatus
  nodes: DeploymentNodePayload[]
  solution_package?: SolutionPackagePayload
  patch_histories: PatchHistoryPayload[]
  visit_histories: VisitHistoryPayload[]
  access_credentials?: AccessCredentials
}

export interface SiteUpdatePayload {
  site_name?: string
  maintenance_company?: string
  customer_info?: ContactInfo
  maintenance_info?: ContactInfo
  contract_start_date?: string
  contract_end_date?: string
  contract_type?: ContractType
  status?: SiteStatus
  access_credentials?: AccessCredentials
}
