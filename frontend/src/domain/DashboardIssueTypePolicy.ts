// frontend/src/domain/DashboardIssueTypePolicy.ts
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
