// frontend/src/presentation/config/queryKeys.ts
export const QUERY_KEYS = {
  me:            () => ['me'] as const,
  latestReport:  () => ['reports', 'latest'] as const,
  reportById:    (id: number) => ['reports', id] as const,
  allReports:    (page: number, size: number) => ['reports', 'list', page, size] as const,
  allReportsBase: () => ['reports'] as const,
  config:        () => ['config'] as const,
  sites:         () => ['sites'] as const,
  siteById:      (id: number) => ['sites', id] as const,
  partnerOrgs:   () => ['partners', 'orgs'] as const,
  partnerIssues: (orgId: string) => ['partners', 'issues', orgId] as const,
} as const
