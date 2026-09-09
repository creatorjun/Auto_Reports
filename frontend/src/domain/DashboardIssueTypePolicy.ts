// frontend/src/domain/DashboardIssueTypePolicy.ts
import type { Semester } from './Dashboard'

const DASHBOARD_EXCLUDED_ISSUE_TYPES = new Set([
  '라이선스',
  '라이센스',
  '라이선스 요청',
  '라이센스 요청',
])

const DASHBOARD_HIDDEN_FILTER_ISSUE_TYPES = new Set([
  '승인된 서비스 요청',
  '케이스',
])

export function isDashboardExcludedIssueType(issueType: string): boolean {
  return DASHBOARD_EXCLUDED_ISSUE_TYPES.has(issueType.normalize('NFKC').trim())
}

export function isDashboardIssueTypeFilterOption(issueType: string): boolean {
  return !isDashboardExcludedIssueType(issueType)
    && !DASHBOARD_HIDDEN_FILTER_ISSUE_TYPES.has(issueType.normalize('NFKC').trim())
}

export function isDashboardIssueTypeIncluded(
  issueType: string,
  selectedTypes: ReadonlySet<string> | null,
  controlledTypes: ReadonlySet<string>,
): boolean {
  return !isDashboardExcludedIssueType(issueType)
    && (selectedTypes === null || !controlledTypes.has(issueType) || selectedTypes.has(issueType))
}

export function isDashboardMonthInSemester(semester: Semester, month: number): boolean {
  return semester === 'h1' ? month >= 1 && month <= 6 : month >= 7 && month <= 12
}

export function isDashboardDateInSemester(value: string, year: number, semester: Semester): boolean {
  const dateYear = Number.parseInt(value.slice(0, 4), 10)
  const month = Number.parseInt(value.slice(5, 7), 10)
  return dateYear === year && isDashboardMonthInSemester(semester, month)
}
