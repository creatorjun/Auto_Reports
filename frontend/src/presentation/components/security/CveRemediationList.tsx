// frontend/src/presentation/components/security/CveRemediationList.tsx
import { ArrowRight, ExternalLink, ShieldAlert } from 'lucide-react'
import type { SecurityNewsItem } from '@/domain/SecurityNews'
import { cveReferenceUrl, safeSecurityNewsUrl } from '@/application/services/securityNews'
import { securityDateLabel, securitySeverityLabels } from './SecurityNewsCard'

const severityClasses = { critical: 'badge-critical', high: 'badge-warning', medium: 'badge-neutral', low: 'badge-good', unknown: 'badge-neutral' }

export default function CveRemediationList({ items, sources }: { items: SecurityNewsItem[]; sources: ReadonlyMap<string, string> }) {
  return <div className="overflow-hidden rounded-2xl border border-apple-divider/70 bg-apple-surface shadow-apple-sm">
    <div aria-hidden="true" className="hidden grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-6 border-b border-apple-divider bg-apple-gray px-5 py-3 text-caption font-semibold text-apple-mid lg:grid">
      <span>CVE · 위험도</span><div className="grid grid-cols-[minmax(0,1fr)_1.5rem_minmax(0,1fr)] gap-3"><span>영향받는 라이브러리 / 버전</span><span /><span>해결된 라이브러리 / 버전</span></div>
    </div>
    {items.map((item) => {
      const url = safeSecurityNewsUrl(item.url)
      const remediations = item.remediations?.length ? item.remediations : [{ vendor: item.vendor, product: item.product || '제품 확인 필요', affected_versions: '', fixed_version: null, reference_url: null }]
      return <article key={item.id} aria-label={item.cve_ids.join(', ') || 'CVE 취약점'} className="grid min-w-0 gap-4 border-b border-apple-divider/70 p-4 last:border-b-0 md:p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:gap-6">
        <div className="min-w-0 space-y-2.5">
          <h2 className="flex flex-wrap gap-2 text-label font-semibold text-apple-dark">{item.cve_ids.length ? item.cve_ids.map((id) => {
            const href = cveReferenceUrl(id)
            return href ? <a key={id} href={href} target="_blank" rel="noopener noreferrer" className="break-all rounded hover:text-brand-600 focus-visible:outline-brand-500">{id}</a> : <span key={id}>{id}</span>
          }) : 'CVE 번호 미제공'}</h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className={severityClasses[item.severity]}>{securitySeverityLabels[item.severity]}{item.cvss_score !== null ? ` · CVSS ${item.cvss_score.toFixed(1)}` : ''}</span>
            {item.known_exploited && <span className="badge-critical gap-1"><ShieldAlert size={12} aria-hidden="true" />실제 악용 확인</span>}
          </div>
          <p className="text-caption text-apple-light">{sources.get(item.source_id) ?? item.source_id} · {item.source_id === 'cisa-kev' ? 'KEV 등록' : item.published_at ? '공개' : '수정'} {securityDateLabel(item.published_at ?? item.updated_at)}</p>
          {url && <a href={url} target="_blank" rel="noopener noreferrer" aria-label={`${item.cve_ids.join(', ')} 원문 확인`} className="inline-flex items-center gap-1 rounded text-caption font-medium text-brand-600 hover:underline focus-visible:outline-brand-500">원문 확인<ExternalLink size={12} aria-hidden="true" /></a>}
        </div>
        <div className="min-w-0 space-y-3">
          {remediations.map((entry, index) => {
            const reference = entry.reference_url ? safeSecurityNewsUrl(entry.reference_url) : null
            const product = [entry.vendor, entry.product].filter(Boolean).join(' / ')
            return <div key={`${product}:${entry.affected_versions}:${index}`} className="grid min-w-0 grid-cols-[minmax(0,1fr)_1rem_minmax(0,1fr)] items-start gap-2 rounded-xl bg-apple-gray/70 p-3 lg:grid-cols-[minmax(0,1fr)_1.5rem_minmax(0,1fr)] lg:gap-3">
              <div className="min-w-0 break-words [overflow-wrap:anywhere]"><span className="mb-1 block text-caption text-apple-light lg:sr-only">영향 버전</span><p className="text-control font-semibold text-apple-dark">{product}</p><p className="mt-1 break-keep text-label text-apple-mid">{entry.affected_versions || '버전 확인 필요'}</p></div>
              <ArrowRight size={16} aria-label="업데이트 대상" className="mt-7 shrink-0 text-apple-light lg:mt-1" />
              <div className="min-w-0 break-words [overflow-wrap:anywhere]"><span className="mb-1 block text-caption text-apple-light lg:sr-only">해결 버전</span><p className="text-control font-semibold text-apple-dark">{product}</p><p className={`mt-1 text-label font-medium ${entry.fixed_version ? 'text-brand-600' : 'text-apple-mid'}`}>{entry.fixed_version || '해결 버전 미확인'}</p>{reference && entry.fixed_version && <a href={reference} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 rounded text-caption text-brand-600 hover:underline focus-visible:outline-brand-500">근거 확인<ExternalLink size={12} aria-hidden="true" /></a>}</div>
            </div>
          })}
        </div>
      </article>
    })}
  </div>
}
