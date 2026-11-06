// frontend/src/application/services/securityNews.ts
import type { SecurityNewsFilters, SecurityNewsItem, SecurityNewsLanguage, SecuritySeverity } from '@/domain/SecurityNews'
import { normalizeSearchText } from '@/domain/Search'

const severityOrder: Record<SecuritySeverity, number> = { critical: 4, high: 3, medium: 2, low: 1, unknown: 0 }

export function defaultSecurityNewsFilters(): SecurityNewsFilters {
  return { kind: 'all', search: '', source: '', severity: 'all', exploitedOnly: false, days: 'all', sort: 'newest' }
}

export function securityNewsTimestamp(item: SecurityNewsItem): number | null {
  for (const value of [item.published_at, item.updated_at]) {
    if (value) {
      const time = Date.parse(value)
      if (Number.isFinite(time)) return time
    }
  }
  return null
}

function matchesSecurityNewsFilters(item: SecurityNewsItem, filters: SecurityNewsFilters, now: number, timestamp: number | null): boolean {
  if (filters.kind === 'updates') {
    if (item.kind !== 'advisory' && item.kind !== 'news') return false
  } else if (filters.kind !== 'all' && item.kind !== filters.kind) return false
  if (filters.source && item.source_id !== filters.source) return false
  if (filters.severity === 'high-risk') {
    if (item.severity !== 'critical' && item.severity !== 'high') return false
  } else if (filters.severity !== 'all' && item.severity !== filters.severity) return false
  if (filters.exploitedOnly && !item.known_exploited) return false
  const threshold = filters.days === 'all' ? null : now - filters.days * 86400000
  return threshold === null || (timestamp !== null && timestamp >= threshold)
}

function securityNewsSearchText(item: SecurityNewsItem, metadata: (string | null | undefined)[]): string {
  return normalizeSearchText([item.title, item.summary, item.original_description, item.title_ko, item.summary_ko, item.vendor, item.product, ...item.cve_ids, ...metadata].filter(Boolean).join(' '))
}

function compareSecurityNews(left: SecurityNewsItem, right: SecurityNewsItem, sort: SecurityNewsFilters['sort'], leftTimestamp: number | null, rightTimestamp: number | null): number {
  if (sort === 'severity') {
    const difference = severityOrder[right.severity] - severityOrder[left.severity]
    if (difference) return difference
    const scoreDifference = (right.cvss_score ?? -1) - (left.cvss_score ?? -1)
    if (scoreDifference) return scoreDifference
  }
  const difference = (rightTimestamp ?? 0) - (leftTimestamp ?? 0)
  return difference || left.id.localeCompare(right.id)
}

export function filterSecurityNews(items: readonly SecurityNewsItem[], filters: SecurityNewsFilters, now: number): SecurityNewsItem[] {
  const terms = normalizeSearchText(filters.search).split(/\s+/).filter(Boolean)
  const result: { item: SecurityNewsItem; timestamp: number | null }[] = []
  for (const item of items) {
    const timestamp = securityNewsTimestamp(item)
    if (!matchesSecurityNewsFilters(item, filters, now, timestamp)) continue
    if (terms.length) {
      const versions = (item.remediations ?? []).flatMap((entry) => [entry.vendor, entry.product, entry.affected_versions, entry.fixed_version])
      const searchable = securityNewsSearchText(item, versions)
      if (!terms.every((term) => searchable.includes(term))) continue
    }
    result.push({ item, timestamp })
  }
  return result.sort((left, right) => compareSecurityNews(left.item, right.item, filters.sort, left.timestamp, right.timestamp)).map(({ item }) => item)
}

export function securityNewsDisplayText(item: SecurityNewsItem, language: SecurityNewsLanguage) {
  if (language === 'original') return { text: item.title, summarized: false, originalFallback: false }
  const summaryKo = item.summary_ko?.trim()
  const summarized = !!summaryKo && !item.title_ko?.trim() && Array.from(summaryKo).length <= 180 && !/[\r\n\v\f\x85\u2028\u2029]/u.test(summaryKo)
  return {
    text: summarized ? summaryKo : item.title,
    summarized,
    originalFallback: !summarized && !!item.title.trim() && !/[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]/u.test(item.title),
  }
}

export function safeSecurityNewsUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return (url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}

export function cveReferenceUrl(value: string): string | null {
  return /^CVE-\d{4}-\d{4,}$/i.test(value) ? `https://nvd.nist.gov/vuln/detail/${value.toUpperCase()}` : null
}
