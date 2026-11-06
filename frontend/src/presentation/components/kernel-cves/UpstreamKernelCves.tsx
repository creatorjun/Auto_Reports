// frontend/src/presentation/components/kernel-cves/UpstreamKernelCves.tsx
import { useEffect, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import type { CveCoverageStatus } from '@/domain/Cve'
import { safeSecurityNewsUrl } from '@/application/services/securityNews'
import { useUpstreamKernelCves } from '@/presentation/hooks/useKernelCves'
import { securityDateLabel } from '@/presentation/components/security/securityNewsFormatting'

const sourceStatus: Record<CveCoverageStatus, string> = {
  ready: '자료 확인 완료', stale: '이전 수집 자료 표시', partial: '일부 자료만 비교', pending: '수집 대기', error: '자료 수집 실패',
}
const button = 'rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control font-medium text-apple-dark hover:bg-apple-gray disabled:opacity-40'
const pageSize = 20

function UpstreamList({ target }: { target: string }) {
  const [filters, setFilters] = useState({ search: '', page: 1 })
  const [draft, setDraft] = useState('')
  const query = useUpstreamKernelCves({ target, ...filters, page_size: pageSize })
  const data = query.data
  const total = data?.total ?? null
  const pages = total === null ? 1 : Math.max(1, Math.ceil(total / pageSize))
  useEffect(() => {
    if (total !== null && filters.page > pages) setFilters((previous) => ({ ...previous, page: pages }))
  }, [filters.page, pages, total])
  return <div className="space-y-3 border-t border-apple-divider p-4 sm:px-5">
    <p className="text-control text-apple-mid">OSV의 Linux 커널 CVE 중 선택한 배포판의 수집된 권고에서 찾지 못한 항목입니다. 선택한 커널 버전에 대한 영향 여부는 미확인입니다.</p>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p role="status" className="text-caption text-apple-mid">
        {data ? <>OSV · {sourceStatus[data.status]}{data.refreshing && ' · 갱신 중'}{data.as_of && ` · 수집 ${securityDateLabel(data.as_of, true)}`}</> : query.isFetching ? 'OSV 자료 조회 중' : '자료 미확인'}
      </p>
      <form className="flex min-w-0 gap-2" onSubmit={(event) => { event.preventDefault(); setFilters({ search: draft.trim(), page: 1 }) }}>
        <input type="search" aria-label="미연결 CVE 검색" value={draft} maxLength={100} placeholder="미연결 CVE 검색" onChange={(event) => {
          const value = event.target.value
          setDraft(value)
          if (!value) setFilters({ search: '', page: 1 })
        }} className="w-40 min-w-0 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark" />
        <button className={button} type="submit">검색</button>
      </form>
    </div>
    {(query.isError || data?.status === 'error' || data?.status === 'stale' || data?.status === 'partial') &&
      <div role="alert" className="flex flex-wrap items-center gap-2 text-control text-apple-mid">
        최신 출처 전체를 확인하지 못했습니다.
        <button type="button" className="font-semibold text-brand-600 underline" disabled={query.isFetching} onClick={() => void query.refetch()}>다시 조회</button>
      </div>}
    {total !== null && <p className="text-control text-apple-mid">검색 결과 <strong className="text-apple-dark">{total.toLocaleString('ko-KR')}건</strong></p>}
    {data && data.items.length > 0 ? <ul className="divide-y divide-apple-divider border-y border-apple-divider">
      {data.items.map((item) => {
        const url = safeSecurityNewsUrl(item.url)
        return <li key={item.cve_id} className="grid gap-1 py-3 text-control text-apple-dark sm:grid-cols-[minmax(10rem,auto)_1fr_auto] sm:gap-3">
          {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-mono font-semibold text-brand-600 hover:underline">{item.cve_id}<ExternalLink size={12} aria-hidden="true" /></a> : <strong>{item.cve_id}</strong>}
          <span className="break-words">{item.title !== item.cve_id ? item.title : '제목 미제공'}</span>
          {item.published_at && <time dateTime={item.published_at} className="text-caption text-apple-mid">등록 {securityDateLabel(item.published_at)}</time>}
        </li>
      })}
    </ul> : <p className="py-3 text-center text-control text-apple-mid">{total === 0 && data?.status === 'ready' && !query.isError ? '검색 조건에 해당하는 미연결 CVE가 없습니다.' : '비교 가능한 CVE 자료를 확인 중이거나 수집 범위가 제한되어 있습니다.'}</p>}
    {total !== null && pages > 1 && <nav aria-label="미연결 CVE 페이지" className="flex items-center justify-end gap-3 text-caption text-apple-mid">
      <button type="button" aria-label="미연결 CVE 이전 페이지" className={button} disabled={filters.page <= 1} onClick={() => setFilters((prev) => ({ ...prev, page: prev.page - 1 }))}><ChevronLeft size={16} /></button>
      <span className="tabular-nums">{filters.page} / {pages}</span>
      <button type="button" aria-label="미연결 CVE 다음 페이지" className={button} disabled={filters.page >= pages} onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}><ChevronRight size={16} /></button>
    </nav>}
  </div>
}

export default function UpstreamKernelCves({ target }: { target: string }) {
  const [expanded, setExpanded] = useState(false)
  return <section aria-label="배포판 권고 미연결 CVE" className="rounded-2xl border border-apple-divider bg-apple-surface">
    <h2><button type="button" aria-expanded={expanded} aria-controls="upstream-kernel-cves" onClick={() => setExpanded(!expanded)} className="flex w-full items-center justify-between gap-2 rounded-2xl px-4 py-4 text-left text-label font-semibold text-apple-dark focus-visible:outline-brand-500 sm:px-5">
      배포판 권고 미연결 CVE <ChevronDown aria-hidden="true" size={16} className={expanded ? 'rotate-180' : ''} />
    </button></h2>
    <div id="upstream-kernel-cves" hidden={!expanded}>{expanded && <UpstreamList target={target} />}</div>
  </section>
}
