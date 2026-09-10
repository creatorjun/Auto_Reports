// frontend/src/domain/Partner.ts
import type { BaseIssue } from './Issue'
import type { Semester } from './Dashboard'
import {
  isDashboardDateInSemester,
  isDashboardIssueTypeIncluded,
  isLicenseIssueType,
} from './DashboardIssueTypePolicy'
import { isDashboardStatusIncluded } from './DashboardStatusPolicy'

export interface PartnerOrg {
  id: string
  name: string
  issue_count: number
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

export function sortPartnerOrganizationsByIssueCount(organizations: PartnerOrg[]): PartnerOrg[] {
  return [...organizations].sort((left, right) => (
    right.issue_count - left.issue_count
    || left.name.localeCompare(right.name, 'ko-KR', { numeric: true, sensitivity: 'base' })
    || left.id.localeCompare(right.id)
  ))
}

export function filterPartnerIssues(
  issues: PartnerIssue[],
  selectedTypes: ReadonlySet<string> | null,
  controlledTypes: string[],
  selectedStatuses: ReadonlySet<string> | null,
  selectedSemester: Semester | null,
  reportYear: number,
): PartnerIssue[] {
  const controlledTypeSet = new Set(controlledTypes)
  return issues.filter((issue) => (
    !isLicenseIssueType(issue.type)
    && isDashboardIssueTypeIncluded(issue.type, selectedTypes, controlledTypeSet)
    && isDashboardStatusIncluded(issue.status, selectedStatuses)
    && (
      selectedSemester === null
      || isDashboardDateInSemester(issue.created, reportYear, selectedSemester)
    )
  ))
}
