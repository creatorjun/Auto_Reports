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

export function filterSecurityNews(items: readonly SecurityNewsItem[], filters: SecurityNewsFilters, now: number): SecurityNewsItem[] {
  const terms = normalizeSearchText(filters.search).split(/\s+/).filter(Boolean)
  const threshold = filters.days === 'all' ? null : now - filters.days * 86400000
  const result: { item: SecurityNewsItem; timestamp: number | null }[] = []
  for (const item of items) {
    if (filters.kind === 'updates') {
      if (item.kind !== 'advisory' && item.kind !== 'news') continue
    } else if (filters.kind !== 'all' && item.kind !== filters.kind) continue
    if (filters.source && item.source_id !== filters.source) continue
    if (filters.severity === 'high-risk') {
      if (item.severity !== 'critical' && item.severity !== 'high') continue
    } else if (filters.severity !== 'all' && item.severity !== filters.severity) continue
    if (filters.exploitedOnly && !item.known_exploited) continue
    const timestamp = securityNewsTimestamp(item)
    if (threshold !== null && (timestamp === null || timestamp < threshold)) continue
    if (terms.length) {
      const searchable = normalizeSearchText([item.title, item.summary, item.title_ko, item.summary_ko, item.vendor, item.product, ...item.cve_ids].filter(Boolean).join(' '))
      if (!terms.every((term) => searchable.includes(term))) continue
    }
    result.push({ item, timestamp })
  }
  return result.sort((left, right) => {
    if (filters.sort === 'severity') {
      const difference = severityOrder[right.item.severity] - severityOrder[left.item.severity]
      if (difference) return difference
      const scoreDifference = (right.item.cvss_score ?? -1) - (left.item.cvss_score ?? -1)
      if (scoreDifference) return scoreDifference
    }
    const difference = (right.timestamp ?? 0) - (left.timestamp ?? 0)
    return difference || left.item.id.localeCompare(right.item.id)
  }).map(({ item }) => item)
}

export function securityNewsDisplayText(item: SecurityNewsItem, language: SecurityNewsLanguage) {
  if (language === 'original') return { title: item.title, summary: item.summary, translated: false, originalFallback: false }
  const titleKo = item.title_ko?.trim()
  const summaryKo = item.summary_ko?.trim()
  const isForeignText = (text: string) => !!text.trim() && !/[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]/u.test(text)
  return {
    title: titleKo || item.title,
    summary: summaryKo || item.summary,
    translated: !!((titleKo && titleKo !== item.title) || (summaryKo && summaryKo !== item.summary)),
    originalFallback: (!titleKo && isForeignText(item.title)) || (!summaryKo && isForeignText(item.summary)),
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
