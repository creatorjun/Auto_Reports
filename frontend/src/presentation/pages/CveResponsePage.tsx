// frontend/src/presentation/pages/CveResponsePage.tsx
import { useEffect, useMemo, useState } from 'react'
import { RefreshCw, Search, ShieldCheck, X } from 'lucide-react'
import type { CveInventoryRequest } from '@/domain/CveInventory'
import { cvePageCount, defaultCveInventoryRequest } from '@/application/services/cveInventory'
import { RequestError } from '@/application/errors/RequestError'
import { useCveInventory } from '@/presentation/hooks/useCveInventory'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import CveInventorySummary from '@/presentation/components/cve/CveInventorySummary'
import CveInventoryCoverage from '@/presentation/components/cve/CveInventoryCoverage'
import CveInventoryResults from '@/presentation/components/cve/CveInventoryResults'
import { cveButtonClass, cveFieldClass, CvePagination } from '@/presentation/components/cve/CveInventoryControls'
import { securityDateLabel } from '@/presentation/components/security/securityNewsFormatting'

export default function CveResponsePage() {
  const [filters, setFilters] = useState(defaultCveInventoryRequest)
  const [search, setSearch] = useState('')
  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((current) => current.search === search.trim() ? current : { ...current, search: search.trim(), page: 1 }), 300)
    return () => window.clearTimeout(timer)
  }, [search])
  const request = useMemo(() => ({ ...filters }), [filters])
  const query = useCveInventory(request)
  const data = query.data
  useEffect(() => {
    if (!data || data.page !== filters.page) return
    const lastPage = cvePageCount(data.total, data.page_size)
    if (filters.page > lastPage) setFilters((current) => ({ ...current, page: lastPage }))
  }, [data, filters.page])
  const update = <K extends keyof CveInventoryRequest>(key: K, value: CveInventoryRequest[K]) => setFilters((current) => ({ ...current, [key]: value, page: key === 'page' ? Number(value) : 1 }))
  const reset = () => { setSearch(''); setFilters(defaultCveInventoryRequest()) }
  const hasFilters = filters.severity !== 'all' || filters.ecosystem !== 'all' || filters.impact !== 'all' || !!search.trim()
  const refreshMessage = query.refreshError instanceof RequestError && query.refreshError.status === 429 ? '다음 갱신 가능 시각까지 기다려 주세요.' : '갱신 요청에 실패했습니다. 마지막으로 수집한 자료를 표시합니다.'
  const progress = data?.progress

  return <div className="mx-auto w-full min-w-0 max-w-content space-y-5 3xl:max-w-none">
    <p className="text-caption text-apple-light">Orcle Linux 8.10 / eyeCloudXoar 4.03_R2 기준</p>
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0"><h1 className="text-page-title font-semibold tracking-tight text-apple-dark">CVE 취약점 대응</h1><p className="mt-2 text-control text-apple-mid">등록한 패키지의 모든 버전 CVE를 확인합니다.</p></div>
      <button type="button" onClick={query.refresh} disabled={!query.canRefresh} aria-busy={query.refreshing} className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50"><RefreshCw size={16} className={query.refreshing ? 'animate-spin' : ''} aria-hidden="true" />{query.refreshing ? '수집 중' : query.retryAfterSeconds > 0 ? `${Math.ceil(query.retryAfterSeconds / 60)}분 후 갱신 가능` : '최신 CVE 확인'}</button>
    </header>
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-caption text-apple-mid">
      {data && <><span>등록 제품 <strong className="font-medium text-apple-dark">{data.inventory.product_count.toLocaleString('ko-KR')}</strong>개</span><span>등록 패키지 <strong className="font-medium text-apple-dark">{data.inventory.package_count.toLocaleString('ko-KR')}</strong>개</span><span>목록 기준 {securityDateLabel(data.inventory.snapshot_at)}</span><span>마지막 수집 {data.refreshed_at ? securityDateLabel(data.refreshed_at, true) : '수집 전'}</span></>}
    </div>
    <CveInventorySummary data={data} selected={filters.severity} onSelect={(severity) => update('severity', severity)} />
    <p className="!mt-2 text-caption text-apple-light">패키지·CVE 조합 기준으로 집계합니다. 파일에 기록된 버전의 영향 여부는 별도로 표시합니다.</p>
    {query.refreshing && <div role="status" className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 text-control text-brand-700"><RefreshCw size={15} className="animate-spin" aria-hidden="true" /><span>패키지 CVE 수집 중{progress && progress.total > 0 ? ` · ${progress.completed.toLocaleString('ko-KR')} / ${progress.total.toLocaleString('ko-KR')}` : ''}</span></div>}
    {(query.isError || query.refreshError || data?.error) && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-control text-amber-800"><p>{query.refreshError ? refreshMessage : query.isError ? data ? '최신 목록을 불러오지 못했습니다. 이전 자료를 표시합니다.' : 'CVE 목록을 불러오지 못했습니다.' : data?.error}</p>{query.isError && <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching} className="rounded-lg px-2 py-1 font-medium underline disabled:opacity-50">다시 조회</button>}</div>}
    {data && <CveInventoryCoverage data={data} />}
    <section aria-label="CVE 검색 필터" className="rounded-2xl border border-apple-divider/70 bg-apple-surface p-4 md:p-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="min-w-0 text-caption font-medium text-apple-mid xl:col-span-2">검색<span className="relative mt-2 block"><Search size={16} className="pointer-events-none absolute left-3 top-3.5 text-apple-light" aria-hidden="true" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} maxLength={200} placeholder="패키지명, CVE 번호, 제품명 검색" className={`${cveFieldClass} pl-9`} /></span></label>
        <label className="min-w-0 text-caption font-medium text-apple-mid">생태계·OS<select value={filters.ecosystem} onChange={(event) => update('ecosystem', event.target.value)} className={`${cveFieldClass} mt-2`}><option value="all">전체 생태계·OS</option>{data?.ecosystems.map((ecosystem) => <option key={ecosystem} value={ecosystem}>{ecosystem}</option>)}</select></label>
        <label className="min-w-0 text-caption font-medium text-apple-mid">파일 버전 영향<select value={filters.impact} onChange={(event) => update('impact', event.target.value as CveInventoryRequest['impact'])} className={`${cveFieldClass} mt-2`}><option value="all">전체 · 모든 버전 CVE</option><option value="affected">파일 버전이 영향받음</option><option value="not_affected">파일 버전이 영향받지 않음</option><option value="unknown">파일 버전 영향 확인 필요</option></select></label>
      </div>
      {hasFilters && <div className="mt-3 flex justify-end"><button type="button" className={cveButtonClass} onClick={reset}><X size={14} aria-hidden="true" />필터 초기화</button></div>}
    </section>
    <section id="cve-inventory-results" aria-label="CVE 조회 결과" aria-busy={query.isFetching} className="min-w-0 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-control text-apple-mid">검색 결과 <strong className="font-semibold tabular-nums text-apple-dark">{data ? data.total.toLocaleString('ko-KR') : '—'}</strong>건<span className="ml-2 text-caption">전체 등록 기간</span></p><div className="flex flex-wrap items-center gap-3"><label className="flex items-center gap-2 text-caption text-apple-mid">표시<select value={filters.page_size} onChange={(event) => update('page_size', Number(event.target.value))} className={`${cveFieldClass} !w-auto`}><option value={20}>20개</option><option value={50}>50개</option><option value={100}>100개</option></select></label><label className="flex items-center gap-2 text-caption text-apple-mid"><span className="sr-only">CVE 정렬</span><select value={filters.sort} onChange={(event) => update('sort', event.target.value as CveInventoryRequest['sort'])} className={`${cveFieldClass} !w-auto`}><option value="severity">위험도순</option><option value="newest">최근 확인순</option><option value="package">패키지명순</option></select></label></div></div>
      {query.isPending ? <div className="rounded-2xl border border-apple-divider bg-apple-surface"><LoadingSpinner text="등록 패키지의 CVE를 불러오는 중입니다." /></div> : data?.items.length ? <CveInventoryResults rows={data.items} /> : <div className="rounded-2xl border border-apple-divider bg-apple-surface px-5 py-12 text-center"><ShieldCheck size={28} className="mx-auto text-apple-light" aria-hidden="true" /><h2 className="mt-4 text-section-title font-semibold text-apple-dark">{query.isError ? '수집 상태를 확인해 주세요' : hasFilters ? '조건에 맞는 CVE가 없습니다' : query.refreshing || !data?.initialized ? '패키지 CVE 수집을 기다리고 있습니다' : '등록 패키지에서 수집된 CVE가 없습니다'}</h2><p className="mt-2 text-control text-apple-mid">{hasFilters ? '위험도·검색·파일 버전 영향 필터를 조정해 보세요.' : '조회하지 못한 패키지는 패키지 수집 현황에서 확인할 수 있습니다.'}</p>{hasFilters && <button type="button" className={`${cveButtonClass} mt-4`} onClick={reset}>필터 초기화</button>}</div>}
      {data && <CvePagination page={data.page} total={data.total} pageSize={data.page_size} onPage={(page) => update('page', page)} label="CVE 목록" disabled={query.isFetching} />}
    </section>
  </div>
}
