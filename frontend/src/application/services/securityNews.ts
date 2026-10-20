// frontend/src/application/services/securityNews.ts
import type { SecurityNewsFilters, SecurityNewsItem, SecuritySeverity } from '@/domain/SecurityNews'
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

export function filterSecurityNews(items: readonly SecurityNewsItem[], filters: SecurityNewsFilters, now: number): SecurityNewsItem[] {
  const terms = normalizeSearchText(filters.search).split(/\s+/).filter(Boolean)
  const threshold = filters.days === 'all' ? null : now - filters.days * 86400000
  return items.filter((item) => {
    if (filters.kind !== 'all' && item.kind !== filters.kind) return false
    if (filters.source && item.source_id !== filters.source) return false
    if (filters.severity !== 'all' && item.severity !== filters.severity) return false
    if (filters.exploitedOnly && !item.known_exploited) return false
    const timestamp = securityNewsTimestamp(item)
    if (threshold !== null && (timestamp === null || timestamp < threshold)) return false
    if (terms.length) {
      const searchable = normalizeSearchText([item.title, item.summary, item.vendor, item.product, ...item.cve_ids].filter(Boolean).join(' '))
      if (!terms.every((term) => searchable.includes(term))) return false
    }
    return true
  }).sort((left, right) => {
    if (filters.sort === 'severity') {
      const difference = severityOrder[right.severity] - severityOrder[left.severity]
      if (difference) return difference
      const scoreDifference = (right.cvss_score ?? -1) - (left.cvss_score ?? -1)
      if (scoreDifference) return scoreDifference
    }
    const difference = (securityNewsTimestamp(right) ?? 0) - (securityNewsTimestamp(left) ?? 0)
    return difference || left.id.localeCompare(right.id)
  })
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
