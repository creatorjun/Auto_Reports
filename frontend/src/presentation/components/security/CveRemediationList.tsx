// frontend/src/presentation/components/security/CveRemediationList.tsx
import { ArrowDown, ArrowUp, ArrowUpDown, ExternalLink, ShieldAlert } from 'lucide-react'
import type { SecurityCveRow, SecurityNewsFilters } from '@/domain/SecurityNews'
import { cveFixedVersionBasisLabel, cveFixedVersionLabel, cveReferenceUrl, isUnknownCveProduct, safeSecurityNewsUrl } from '@/application/services/securityNews'
import { securityDateLabel, securitySeverityLabels } from './securityNewsFormatting'

const severityClasses = { critical: 'badge-critical', high: 'badge-warning', medium: 'badge-neutral', low: 'badge-good', unknown: 'badge-neutral' }
type SortableColumn = 'software' | 'affected-version' | 'fixed-version'

export default function CveRemediationList({ rows, sources, sort = 'newest', onSort }: {
  rows: SecurityCveRow[]
  sources: ReadonlyMap<string, string>
  sort?: SecurityNewsFilters['sort']
  onSort?: (sort: SecurityNewsFilters['sort']) => void
}) {
  const sortHeader = (column: SortableColumn, label: string) => {
    const ascending = sort === column
    const descending = sort === `${column}-desc`
    const Icon = ascending ? ArrowUp : descending ? ArrowDown : ArrowUpDown
    return <th scope="col" aria-sort={ascending ? 'ascending' : descending ? 'descending' : 'none'} className="px-4 py-3 font-medium">
      <button type="button" onClick={() => onSort?.(ascending ? `${column}-desc` : column)} className={`inline-flex items-center gap-1.5 rounded focus-visible:outline-brand-500 ${ascending || descending ? 'text-brand-600' : 'hover:text-apple-dark'}`} aria-label={`${label} ${ascending ? '내림차순' : '오름차순'} 정렬`}>
        {label}<Icon size={13} aria-hidden="true" />
      </button>
    </th>
  }
  return <div className="overflow-hidden rounded-2xl border border-apple-divider/70 bg-apple-surface shadow-apple-sm">
    <div role="region" aria-label="CVE 취약점 대응표 · 가로 스크롤" tabIndex={0} className="overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500">
      <table className="w-full min-w-[1280px] whitespace-nowrap text-left text-control">
        <caption className="sr-only">소프트웨어와 버전 대응별 한 행으로 표시하는 CVE 목록</caption>
        <thead className="border-b border-apple-divider bg-apple-gray text-caption text-apple-mid">
          <tr>
            <th scope="col" className="sticky left-0 z-10 bg-apple-gray px-4 py-3 font-medium">CVE</th>
            <th scope="col" className="px-4 py-3 font-medium">위험도 · CVSS</th>
            {sortHeader('software', '소프트웨어')}
            {sortHeader('affected-version', '영향 버전')}
            {sortHeader('fixed-version', '해결 버전')}
            <th scope="col" className="px-4 py-3 font-medium">판단 근거</th>
            <th scope="col" className="px-4 py-3 font-medium">실제 악용</th>
            <th scope="col" className="px-4 py-3 font-medium">출처</th>
            <th scope="col" className="px-4 py-3 font-medium">등록·공개일</th>
            <th scope="col" className="px-4 py-3 font-medium">원문</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-apple-divider/60">
          {rows.map(({ id, item, remediation: entry }) => {
            const url = safeSecurityNewsUrl(item.url)
            const reference = entry.reference_url ? safeSecurityNewsUrl(entry.reference_url) : null
            const unknownProduct = isUnknownCveProduct(entry.product)
            const product = unknownProduct ? '제품 확인 필요' : entry.product
            const software = unknownProduct || !entry.vendor || product.toLocaleLowerCase().startsWith(`${entry.vendor.toLocaleLowerCase()} `) ? product : `${entry.vendor} / ${product}`
            const affected = entry.affected_versions || '버전 확인 필요'
            const fixed = cveFixedVersionLabel(entry)
            const basis = cveFixedVersionBasisLabel(entry)
            const evidenceUrl = entry.fixed_version ? reference ?? url : null
            const basisDetail = !entry.fixed_version ? '확인된 해결 버전이나 적용 가능한 영향 범위 경계가 없습니다.' : entry.fixed_version_basis === 'nvd_range' ? '이 CVE의 같은 제품과 주·부 버전 계열의 다른 NVD 영향 범위까지 확인한 경계입니다. 다른 CVE나 버전 계열, 설치 환경, 공급사 백포트의 해결 여부를 보장하지 않습니다.' : entry.fixed_version_basis === 'vendor' ? '제조사가 제공한 취약점 설명과 제조사 보안 공지 출처로 확인한 수정 버전입니다.' : entry.fixed_version_basis === 'description' ? '수집한 원문 설명에 수정 버전이 명시되어 있습니다. 제조사 확인과 구분합니다.' : '기존에 수집한 해결 버전이며 판단 근거는 아직 확인되지 않았습니다.'
            return <tr key={id} className="group text-apple-mid hover:bg-apple-gray/60">
              <th scope="row" className="sticky left-0 z-10 bg-apple-surface px-4 py-3 text-left font-medium text-apple-dark group-hover:bg-apple-gray">
                {item.cve_ids.length ? item.cve_ids.map((cve, index) => {
                  const href = cveReferenceUrl(cve)
                  return <span key={cve}>{index > 0 && ', '}{href ? <a href={href} target="_blank" rel="noopener noreferrer" className="rounded hover:text-brand-600 focus-visible:outline-brand-500">{cve}</a> : cve}</span>
                }) : 'CVE 번호 미제공'}
              </th>
              <td className="px-4 py-3"><span className="inline-flex items-center gap-2"><span className={severityClasses[item.severity]}>{securitySeverityLabels[item.severity]}</span><span className="tabular-nums" title={item.cvss_version ? `CVSS v${item.cvss_version}` : undefined}>{item.cvss_score !== null ? item.cvss_score.toFixed(1) : '—'}</span></span></td>
              <td className="px-4 py-3"><span className={`block max-w-64 truncate ${unknownProduct ? 'text-apple-light' : 'font-medium text-apple-dark'}`} title={software}>{software}</span></td>
              <td className="px-4 py-3"><span className="block max-w-72 truncate tabular-nums" title={affected}>{affected}</span></td>
              <td className="px-4 py-3"><span className={`block max-w-56 truncate tabular-nums ${entry.fixed_version ? 'font-medium text-brand-600' : 'text-apple-light'}`} title={fixed}>{fixed}</span></td>
              <td className="px-4 py-3 text-caption" title={basisDetail}>{evidenceUrl ? <a href={evidenceUrl} target="_blank" rel="noopener noreferrer" aria-label={`${item.cve_ids.join(', ')} ${basis} 근거 확인`} className="inline-flex items-center gap-1 rounded text-brand-600 hover:underline focus-visible:outline-brand-500">{basis}<ExternalLink size={12} aria-hidden="true" /></a> : <span className="text-apple-light">{basis}</span>}</td>
              <td className="px-4 py-3">{item.known_exploited ? <span className="inline-flex items-center gap-1.5 text-red-600"><ShieldAlert size={13} aria-hidden="true" />확인</span> : <span className="text-apple-light">—</span>}</td>
              <td className="px-4 py-3 text-caption">{sources.get(item.source_id) ?? item.source_id}</td>
              <td className="px-4 py-3 text-caption tabular-nums" title={item.source_id === 'cisa-kev' ? 'KEV 등록일' : item.published_at ? 'CVE 공개일' : '수정일'}>{securityDateLabel(item.published_at ?? item.updated_at)}</td>
              <td className="px-4 py-3">{url ? <a href={url} target="_blank" rel="noopener noreferrer" aria-label={`${item.cve_ids.join(', ')} 원문 확인`} className="inline-flex items-center gap-1 rounded text-caption text-brand-600 hover:underline focus-visible:outline-brand-500">원문<ExternalLink size={12} aria-hidden="true" /></a> : '—'}</td>
            </tr>
          })}
        </tbody>
      </table>
    </div>
  </div>
}
