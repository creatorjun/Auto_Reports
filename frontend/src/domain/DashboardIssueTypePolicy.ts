// frontend/src/domain/DashboardIssueTypePolicy.ts
const DASHBOARD_EXCLUDED_ISSUE_TYPES = new Set([
  '라이선스',
  '라이센스',
  '라이선스 요청',
  '라이센스 요청',
])

export function isDashboardExcludedIssueType(issueType: string): boolean {
  return DASHBOARD_EXCLUDED_ISSUE_TYPES.has(issueType.normalize('NFKC').trim())
}
