// frontend/src/domain/Partner.ts
export interface PartnerOrg {
  id: string
  name: string
}

export interface PartnerMember {
  account_id: string
  display_name: string
  email: string
}

export interface PartnerIssue {
  key: string
  summary: string
  type: string
  status: string
  stage_index: number
  created: string
  elapsed_days: number
  reporter: string
  tac_team: string
}
