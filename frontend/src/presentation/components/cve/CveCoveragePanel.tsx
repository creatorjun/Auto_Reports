// frontend/src/presentation/components/cve/CveCoveragePanel.tsx
import { ExternalLink } from 'lucide-react'
import type { CveCoverage, CveCoverageStatus } from '@/domain/Cve'
import { safeSecurityNewsUrl } from '@/application/services/securityNews'
import { securityDateLabel } from '@/presentation/components/security/securityNewsFormatting'

const statusLabels: Record<CveCoverageStatus, string> = {
  pending: '수집 대기', ready: '수집 완료', partial: '일부 자료만 수집', stale: '이전 수집 자료', error: '수집 실패',
}

export default function CveCoveragePanel({ coverage }: { coverage: CveCoverage }) {
  const warning = coverage.status !== 'ready' && coverage.status !== 'pending'
  const successes = coverage.sources.flatMap((source) => source.refreshed_at ? [source.refreshed_at] : [])
  const lastSuccess = successes.sort((a, b) => Date.parse(b) - Date.parse(a))[0]
  return (
    <section aria-label="공식 자료 수집 상태" className={`rounded-xl border px-4 py-3 text-control ${warning ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-apple-divider bg-apple-surface text-apple-mid'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p role="status" className="font-semibold">공식 자료 · {statusLabels[coverage.status]}{coverage.refreshing && (lastSuccess ? ' · 새 자료 수집 중, 이전 결과 표시' : ' · 수집 중')}</p>
          {lastSuccess && <p className="mt-1 text-caption">최근 출처 수집 성공 <time dateTime={lastSuccess}>{securityDateLabel(lastSuccess, true)}</time> KST</p>}
        </div>
        {coverage.sources.length > 0 && <details className="min-w-0 max-w-full text-caption">
          <summary className="cursor-pointer rounded underline underline-offset-2">출처 {coverage.sources.length}개</summary>
          <ul className="mt-2 space-y-2">
            {coverage.sources.map((source) => {
              const href = safeSecurityNewsUrl(source.url)
              return <li key={source.id}>
                {href ? <a className="inline-flex items-center gap-1 font-medium underline" href={href} target="_blank" rel="noopener noreferrer">{source.label}<ExternalLink size={12} aria-hidden="true" /></a> : source.label}
                {' · '}{statusLabels[source.status]}{source.refreshed_at && ` · ${securityDateLabel(source.refreshed_at, true)}`}
                {source.note && <p className="mt-1">{source.note}</p>}
              </li>
            })}
          </ul>
        </details>}
      </div>
      {coverage.coverage_note && <p className="mt-1.5 leading-relaxed">{coverage.coverage_note}</p>}
      {warning && <p className="mt-1.5">누락되었거나 아직 반영되지 않은 CVE가 있을 수 있습니다.</p>}
    </section>
  )
}
