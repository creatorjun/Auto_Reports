// frontend/src/domain/Partner.ts
import type { BaseIssue } from './Issue'

export interface PartnerOrg {
  id: string
  name: string
}

export interface PartnerMember {
  account_id: string
  display_name: string
  email: string
}

export type PartnerIssue = BaseIssue

export function normalizePartnerSearch(value: string): string {
  return value.normalize('NFKC').trim().toLocaleLowerCase('ko-KR')
}

export function matchesPartnerSearch(value: string, normalizedQuery: string): boolean {
  return normalizePartnerSearch(value).includes(normalizedQuery)
}
