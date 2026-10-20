// frontend/src/presentation/components/security/SecurityNewsSources.tsx
import { ChevronDown, ExternalLink, Radio } from 'lucide-react'
import type { SecurityNewsSource } from '@/domain/SecurityNews'
import { safeSecurityNewsUrl } from '@/application/services/securityNews'
import { securityDateLabel } from './SecurityNewsCard'

const statusLabels = { ok: '정상', stale: '이전 자료 표시', error: '수집 실패', pending: '수집 대기' }
const statusClasses = { ok: 'badge-good', stale: 'badge-warning', error: 'badge-critical', pending: 'badge-neutral' }

export default function SecurityNewsSources({ sources, refreshing }: { sources: SecurityNewsSource[]; refreshing: boolean }) {
  const successful = sources.filter((source) => source.status === 'ok').length
  const hasIssue = sources.some((source) => source.status === 'error' || source.status === 'stale')
  return (
    <details className="group rounded-2xl border border-apple-divider/70 bg-apple-surface">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 rounded-2xl px-4 py-4 text-control focus-visible:outline-brand-500 md:px-5 [&::-webkit-details-marker]:hidden">
        <Radio size={16} className={hasIssue ? 'text-amber-600' : 'text-brand-600'} aria-hidden="true" />
        <span className="font-semibold text-apple-dark">수집 출처</span>
        <span className="text-caption text-apple-mid">{sources.length ? `${successful} / ${sources.length} 정상` : '확인 중'}</span>
        {hasIssue && <span className="text-caption text-amber-700">일부 출처 확인 필요</span>}
        {refreshing && <span className="text-caption text-brand-600">업데이트 중</span>}
        <ChevronDown size={16} className="ml-auto text-apple-light transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="border-t border-apple-divider/60 p-4 md:p-5">
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {sources.map((source) => {
            const url = safeSecurityNewsUrl(source.homepage)
            return (
              <div key={source.id} className="min-w-0 rounded-xl bg-apple-gray p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 break-words text-control font-semibold text-apple-dark hover:text-brand-600">{source.name}<ExternalLink size={12} aria-hidden="true" /></a> : <span className="text-control font-semibold text-apple-dark">{source.name}</span>}
                  <span className={statusClasses[source.status]}>{statusLabels[source.status]}</span>
                </div>
                <p className="mt-3 text-caption text-apple-mid">{source.last_success_at ? `보관 중 ${source.count.toLocaleString('ko-KR')}개 · 마지막 성공 ${securityDateLabel(source.last_success_at, true)}` : '수집에 성공한 기록이 없습니다.'}</p>
                {source.error && <p className="mt-2 break-words text-caption text-amber-700">{source.error}</p>}
                {source.warning && <p className="mt-2 break-words text-caption text-apple-mid">{source.warning}</p>}
              </div>
            )
          })}
        </div>
        <p className="mt-4 text-caption leading-relaxed text-apple-mid">출처별 공개 자료의 일부를 모아 표시합니다. NVD는 최근 7일 내 최신 200건을 최소 2시간 간격으로 확인하며, 다른 출처는 화면 이용 중 약 15분 간격으로 확인합니다. 수집 실패 시 마지막으로 받은 자료를 유지합니다.</p>
      </div>
    </details>
  )
}
