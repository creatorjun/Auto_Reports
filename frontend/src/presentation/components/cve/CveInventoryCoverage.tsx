// frontend/src/presentation/components/cve/CveInventoryCoverage.tsx
import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Database, Search } from 'lucide-react'
import type { CveInventoryPackageRequest, CveInventorySnapshot } from '@/domain/CveInventory'
import { cveCollectionLabels, cvePageCount } from '@/application/services/cveInventory'
import { useCveInventoryPackages } from '@/presentation/hooks/useCveInventory'
import { securityDateLabel } from '@/presentation/components/security/securityNewsFormatting'
import { cveButtonClass, cveFieldClass, CvePagination } from './CveInventoryControls'

export default function CveInventoryCoverage({ data }: { data: CveInventorySnapshot }) {
  const [expanded, setExpanded] = useState(false)
  const [search, setSearch] = useState('')
  const [submittedSearch, setSubmittedSearch] = useState('')
  const [status, setStatus] = useState<CveInventoryPackageRequest['status']>('all')
  const [page, setPage] = useState(1)
  const request = useMemo(() => ({ search: submittedSearch, status, page, page_size: 20 }), [submittedSearch, status, page])
  const packages = useCveInventoryPackages(request, expanded)
  useEffect(() => {
    if (!packages.data || packages.data.page !== page) return
    const lastPage = cvePageCount(packages.data.total, packages.data.page_size)
    if (page > lastPage) setPage(lastPage)
  }, [packages.data, page])
  const unresolved = data.coverage.unmapped + data.coverage.pending + data.coverage.error + data.coverage.stale
  return <section aria-label="패키지 수집 현황" className="rounded-2xl border border-apple-divider/70 bg-apple-surface">
    <button type="button" aria-expanded={expanded} aria-controls="cve-inventory-coverage" onClick={() => setExpanded(!expanded)} className="flex w-full flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-4 text-left focus-visible:outline-brand-500 md:px-5">
      <span className="flex min-w-0 flex-wrap items-center gap-2"><Database size={16} className="text-brand-600" aria-hidden="true" /><span className="text-control font-medium text-apple-dark">패키지 수집 현황</span><span className="text-caption text-apple-mid">조회 완료 {data.coverage.ok.toLocaleString('ko-KR')} / {data.coverage.total.toLocaleString('ko-KR')}</span></span>
      <span className="flex flex-wrap items-center gap-3 text-caption text-apple-mid"><span>매핑 필요 {data.coverage.unmapped.toLocaleString('ko-KR')}</span><span>대기 {data.coverage.pending.toLocaleString('ko-KR')}</span><span className={data.coverage.error + data.coverage.stale ? 'text-amber-700' : ''}>실패·이전 자료 {(data.coverage.error + data.coverage.stale).toLocaleString('ko-KR')}</span>{expanded ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}</span>
    </button>
    {unresolved > 0 && <p className="px-4 pb-4 text-caption text-apple-mid md:px-5">조회 대기·실패·매핑 필요 항목은 취약점 없음으로 판단하지 않습니다.</p>}
    {expanded && <div id="cve-inventory-coverage" className="space-y-4 border-t border-apple-divider/60 p-4 md:p-5">
      <form className="flex flex-wrap items-end gap-3" onSubmit={(event) => { event.preventDefault(); setSubmittedSearch(search); setPage(1) }}>
        <label className="min-w-0 flex-1 basis-56 text-caption font-medium text-apple-mid">등록 패키지 검색<input value={search} onChange={(event) => setSearch(event.target.value)} maxLength={200} placeholder="패키지명 또는 제품명" className={`${cveFieldClass} mt-2`} /></label>
        <label className="min-w-0 basis-44 text-caption font-medium text-apple-mid">수집 상태<select value={status} onChange={(event) => { setStatus(event.target.value as CveInventoryPackageRequest['status']); setPage(1) }} className={`${cveFieldClass} mt-2`}><option value="all">전체 상태</option>{Object.entries(cveCollectionLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <button type="submit" className={cveButtonClass}><Search size={15} aria-hidden="true" />검색</button>
      </form>
      {packages.isError ? <div role="alert" className="flex flex-wrap items-center justify-between gap-3 text-control text-amber-700"><span>패키지 수집 상태를 불러오지 못했습니다.</span><button type="button" className={cveButtonClass} onClick={() => void packages.refetch()} disabled={packages.isFetching}>다시 조회</button></div> : packages.isPending ? <p role="status" className="py-4 text-control text-apple-mid">패키지 수집 상태를 불러오는 중입니다.</p> : <>
        <p role="status" className="text-caption text-apple-mid">등록 패키지 {packages.data?.total.toLocaleString('ko-KR') ?? 0}개</p>
        <ul className="divide-y divide-apple-divider/60">{packages.data?.items.map((item) => <li key={item.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
          <div className="min-w-0 flex-1 basis-64"><p className="break-words text-control font-medium text-apple-dark">{item.name}<span className="ml-2 text-caption font-normal text-apple-mid">{item.ecosystem}</span></p><p className="mt-1 break-words text-caption text-apple-mid">{item.versions.join(' · ') || '기록 버전 없음'}</p>{(item.mapping_reason || item.error) && <p className="mt-2 break-words text-caption text-amber-700">{item.error || item.mapping_reason}</p>}</div>
          <div className="space-y-1 text-right"><span className={item.status === 'ok' ? 'badge-good' : item.status === 'error' || item.status === 'stale' ? 'badge-warning' : 'badge-neutral'}>{cveCollectionLabels[item.status]}</span><p className="text-caption text-apple-mid">{item.status === 'ok' || item.status === 'stale' ? `수집 CVE ${item.cve_count.toLocaleString('ko-KR')}개` : '조회 결과 미확정'}</p>{item.last_success_at && <p className="text-caption text-apple-light">{securityDateLabel(item.last_success_at, true)}</p>}</div>
        </li>)}</ul>
        {packages.data?.items.length === 0 && <p className="py-5 text-center text-control text-apple-mid">조건에 맞는 등록 패키지가 없습니다.</p>}
        {packages.data && <CvePagination page={packages.data.page} total={packages.data.total} pageSize={packages.data.page_size} onPage={setPage} label="등록 패키지" disabled={packages.isFetching} />}
      </>}
    </div>}
  </section>
}
