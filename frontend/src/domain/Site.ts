// frontend/src/domain/Site.ts
export type SiteStatus = 'active' | 'inactive' | 'expired' | 'maintenance'

export interface SiteSummary {
  id: string
  site_name: string
  customer_name: string
  status: SiteStatus
  contract_end_date: string
}

export interface ContactInfo {
  name: string
  phone: string
  email?: string
}

export interface SiteCreatePayload {
  id: string
  site_name: string
  maintenance_company: string
  customer_info: ContactInfo
  maintenance_info: ContactInfo
  contract_start_date: string
  contract_end_date: string
  contract_type: string
  status: SiteStatus
  nodes: []
  patch_histories: []
  visit_histories: []
}
