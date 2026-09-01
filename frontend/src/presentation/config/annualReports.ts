// frontend/src/presentation/config/annualReports.ts
export const ANNUAL_REPORT_YEARS = [2024, 2025, 2026] as const
export const REFRESHABLE_ANNUAL_REPORT_YEAR = 2026
export const REPORT_REFRESH_INTERVAL_MS = 1000 * 60 * 5

export const isRefreshableAnnualReport = (year: number) =>
  year === REFRESHABLE_ANNUAL_REPORT_YEAR
