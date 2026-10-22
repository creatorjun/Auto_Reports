// frontend/src/application/services/securityNews.ts
import type { SecurityCveRemediation, SecurityCveRow, SecurityNewsFilters, SecurityNewsItem, SecurityNewsLanguage, SecuritySeverity } from '@/domain/SecurityNews'
import { normalizeSearchText } from '@/domain/Search'

const severityOrder: Record<SecuritySeverity, number> = { critical: 4, high: 3, medium: 2, low: 1, unknown: 0 }
const softwareCollator = new Intl.Collator('ko-KR', { numeric: true, sensitivity: 'base' })
const versionCollator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' })

export function defaultSecurityNewsFilters(): SecurityNewsFilters {
  return { kind: 'all', search: '', source: '', severity: 'all', exploitedOnly: false, hideUnknownProducts: false, days: 'all', sort: 'newest' }
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

function matchesSecurityNewsFilters(item: SecurityNewsItem, filters: SecurityNewsFilters, now: number): boolean {
  if (filters.kind === 'updates') {
    if (item.kind !== 'advisory' && item.kind !== 'news') return false
  } else if (filters.kind !== 'all' && item.kind !== filters.kind) return false
  if (filters.source && item.source_id !== filters.source) return false
  if (filters.severity === 'high-risk') {
    if (item.severity !== 'critical' && item.severity !== 'high') return false
  } else if (filters.severity !== 'all' && item.severity !== filters.severity) return false
  if (filters.exploitedOnly && !item.known_exploited) return false
  const threshold = filters.days === 'all' ? null : now - filters.days * 86400000
  const timestamp = securityNewsTimestamp(item)
  return threshold === null || (timestamp !== null && timestamp >= threshold)
}

function securityNewsSearchText(item: SecurityNewsItem, metadata: (string | null | undefined)[]): string {
  return normalizeSearchText([item.title, item.summary, item.original_description, item.title_ko, item.summary_ko, item.vendor, item.product, ...item.cve_ids, ...metadata].filter(Boolean).join(' '))
}

function compareSecurityNews(left: SecurityNewsItem, right: SecurityNewsItem, sort: SecurityNewsFilters['sort']): number {
  if (sort === 'severity') {
    const difference = severityOrder[right.severity] - severityOrder[left.severity]
    if (difference) return difference
    const scoreDifference = (right.cvss_score ?? -1) - (left.cvss_score ?? -1)
    if (scoreDifference) return scoreDifference
  }
  const difference = (securityNewsTimestamp(right) ?? 0) - (securityNewsTimestamp(left) ?? 0)
  return difference || left.id.localeCompare(right.id)
}

export function filterSecurityNews(items: readonly SecurityNewsItem[], filters: SecurityNewsFilters, now: number): SecurityNewsItem[] {
  const terms = normalizeSearchText(filters.search).split(/\s+/).filter(Boolean)
  const result: SecurityNewsItem[] = []
  for (const item of items) {
    if (!matchesSecurityNewsFilters(item, filters, now)) continue
    if (terms.length) {
      const versions = (item.remediations ?? []).flatMap((entry) => [entry.vendor, entry.product, entry.affected_versions, entry.fixed_version])
      const searchable = securityNewsSearchText(item, versions)
      if (!terms.every((term) => searchable.includes(term))) continue
    }
    result.push(item)
  }
  return result.sort((left, right) => compareSecurityNews(left, right, filters.sort))
}

export function isUnknownCveProduct(product: string | null | undefined): boolean {
  const normalized = product?.trim()
  return !normalized || normalized === '제품 확인 필요'
}

export function cveFixedVersionBasisLabel(entry: SecurityCveRemediation): string {
  if (!entry.fixed_version) return '미확인'
  if (entry.fixed_version_basis === 'vendor') return '제조사 확인'
  if (entry.fixed_version_basis === 'nvd_range') return 'NVD 영향 범위'
  if (entry.fixed_version_basis === 'description') return '출처 수정 명시'
  return '근거 확인 필요'
}

export function cveFixedVersionLabel(entry: SecurityCveRemediation): string {
  if (!entry.fixed_version) return '해결 버전 미확인'
  if (entry.fixed_version_basis !== 'nvd_range') return entry.fixed_version
  const branch = entry.fixed_version_branch?.trim()
  return branch && /^\d+\.\d+$/.test(branch) && (entry.fixed_version === branch || entry.fixed_version.startsWith(`${branch}.`)) ? `${entry.fixed_version} 이상 (${branch} 계열)` : `${entry.fixed_version} (계열 확인 필요)`
}

function compareCveSoftware(left: SecurityCveRow, right: SecurityCveRow, direction: number): number {
  const leftUnknown = isUnknownCveProduct(left.remediation.product)
  const rightUnknown = isUnknownCveProduct(right.remediation.product)
  if (leftUnknown !== rightUnknown) return leftUnknown ? 1 : -1
  return direction * (softwareCollator.compare(left.remediation.product.trim(), right.remediation.product.trim()) || softwareCollator.compare(left.remediation.vendor?.trim() ?? '', right.remediation.vendor?.trim() ?? ''))
}

function compareCveVersions(left: string | null, right: string | null, direction: number): number {
  const leftVersion = left?.normalize('NFKC').match(/\d.*$/u)?.[0] ?? null
  const rightVersion = right?.normalize('NFKC').match(/\d.*$/u)?.[0] ?? null
  if (leftVersion === null || rightVersion === null) return leftVersion === rightVersion ? 0 : leftVersion === null ? 1 : -1
  return direction * versionCollator.compare(leftVersion, rightVersion)
}

export function filterCveResponseRows(items: readonly SecurityNewsItem[], filters: SecurityNewsFilters, now: number): SecurityCveRow[] {
  const terms = normalizeSearchText(filters.search).split(/\s+/).filter(Boolean)
  const rows: SecurityCveRow[] = []
  for (const item of items) {
    if (item.kind !== 'cve' || !matchesSecurityNewsFilters(item, filters, now)) continue
    const remediations: SecurityCveRemediation[] = item.remediations?.length ? item.remediations : [{ vendor: item.vendor, product: item.product?.trim() || '제품 확인 필요', affected_versions: '', fixed_version: null, reference_url: null }]
    const itemSearchText = terms.length ? securityNewsSearchText(item, []) : ''
    const rowTerms = terms.filter((term) => !itemSearchText.includes(term))
    for (const [index, remediation] of remediations.entries()) {
      if (filters.hideUnknownProducts && isUnknownCveProduct(remediation.product)) continue
      if (rowTerms.length) {
        const searchable = normalizeSearchText([remediation.vendor, remediation.product, remediation.affected_versions, cveFixedVersionLabel(remediation), cveFixedVersionBasisLabel(remediation)].filter(Boolean).join(' '))
        if (!rowTerms.every((term) => searchable.includes(term))) continue
      }
      rows.push({ id: `${item.id}:${index}`, item, remediation })
    }
  }
  const direction = filters.sort.endsWith('-desc') ? -1 : 1
  return rows.sort((left, right) => {
    let difference = 0
    if (filters.sort === 'software' || filters.sort === 'software-desc') {
      difference = compareCveSoftware(left, right, direction) || compareCveVersions(left.remediation.affected_versions, right.remediation.affected_versions, 1)
    } else if (filters.sort === 'affected-version' || filters.sort === 'affected-version-desc') {
      difference = compareCveVersions(left.remediation.affected_versions, right.remediation.affected_versions, direction) || compareCveSoftware(left, right, 1)
    } else if (filters.sort === 'fixed-version' || filters.sort === 'fixed-version-desc') {
      difference = compareCveVersions(left.remediation.fixed_version, right.remediation.fixed_version, direction) || compareCveSoftware(left, right, 1)
    }
    return difference || compareSecurityNews(left.item, right.item, filters.sort) || left.id.localeCompare(right.id)
  })
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
