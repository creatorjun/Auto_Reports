// frontend/src/domain/Site.ts
export type SiteStatus = 'installing' | 'active' | 'inactive' | 'expired' | 'maintenance'

export type ContractType = '정식라이센스' | '임시라이센스'

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
  username?: string
  password?: string
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
  pkg_version?: string
}

export interface DeploymentNode extends DeploymentNodePayload {
  id?: number
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

export interface PatchHistory extends PatchHistoryPayload {
  id?: number
}

export interface VisitHistoryPayload {
  visit_datetime?: string
  engineer_name?: string
  engineer_phone?: string
  request_content?: string
  action_content?: string
}

export interface VisitHistory extends VisitHistoryPayload {
  id?: number
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
