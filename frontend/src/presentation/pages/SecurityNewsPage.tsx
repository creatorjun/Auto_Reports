// frontend/src/presentation/pages/SecurityNewsPage.tsx
import { useMemo, useState } from 'react'
import { ArrowDownWideNarrow, Check, ChevronLeft, ChevronRight, Newspaper, RefreshCw, Search, ShieldAlert, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import type { SecurityNewsFilters, SecurityNewsLanguage } from '@/domain/SecurityNews'
import { RequestError } from '@/application/errors/RequestError'
import { defaultSecurityNewsFilters, filterSecurityNews } from '@/application/services/securityNews'
import { useSecurityNews } from '@/presentation/hooks/useSecurityNews'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SecurityNewsCard, { securityDateLabel, securitySeverityLabels } from '@/presentation/components/security/SecurityNewsCard'
import SecurityNewsSources from '@/presentation/components/security/SecurityNewsSources'
import SecurityNewsTranslationControls from '@/presentation/components/security/SecurityNewsTranslationControls'

const PAGE_SIZE = 20
const summaryFilters = [
  { key: 'all', label: '수집된 항목', icon: Newspaper, color: 'text-brand-600', kind: 'all', severity: 'all', exploitedOnly: false },
  { key: 'exploited', label: '실제 악용 확인', icon: ShieldAlert, color: 'text-red-600', kind: 'all', severity: 'all', exploitedOnly: true },
  { key: 'high', label: '치명적 · 높은 위험도', icon: ShieldCheck, color: 'text-amber-600', kind: 'all', severity: 'high-risk', exploitedOnly: false },
  { key: 'updates', label: '보안 권고 · 뉴스', icon: Newspaper, color: 'text-brand-600', kind: 'updates', severity: 'all', exploitedOnly: false },
] as const
const fieldClass = 'w-full min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30'
const buttonClass = 'inline-flex items-center justify-center gap-2 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control font-medium text-apple-dark transition-colors hover:bg-apple-gray focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-40'

export default function SecurityNewsPage() {
  const query = useSecurityNews()
  const [filters, setFilters] = useState(defaultSecurityNewsFilters)
  const [page, setPage] = useState(0)
  const [language, setLanguage] = useState<SecurityNewsLanguage>('ko')
  const data = query.data
  const items = data?.items
  const filterTime = Math.floor(query.now / 60000) * 60000
  const filtered = useMemo(() => filterSecurityNews(items ?? [], filters, filterTime), [items, filters, filterTime])
  const sources = useMemo(() => new Map(data?.sources.map((source) => [source.id, source.name]) ?? []), [data?.sources])
  const counts = useMemo(() => ({
    all: items?.length ?? 0,
    exploited: items?.filter((item) => item.known_exploited).length ?? 0,
    high: items?.filter((item) => item.severity === 'critical' || item.severity === 'high').length ?? 0,
    updates: items?.filter((item) => item.kind === 'advisory' || item.kind === 'news').length ?? 0,
  }), [items])
  const failedSources = data?.sources.filter((source) => source.status === 'stale' || source.status === 'error') ?? []
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount - 1)
  const hasFilters = filters.kind !== 'all' || !!filters.search.trim() || !!filters.source || filters.severity !== 'all' || filters.exploitedOnly || filters.days !== 'all'
  const selectedSummary = filters.kind === 'updates' ? 'updates' : filters.severity === 'high-risk' ? 'high' : filters.exploitedOnly ? 'exploited' : 'all'
  const update = <K extends keyof SecurityNewsFilters>(key: K, value: SecurityNewsFilters[K]) => {
    setFilters((current) => ({ ...current, [key]: value }))
    setPage(0)
  }
  const reset = () => { setFilters(defaultSecurityNewsFilters()); setPage(0) }
  const selectSummary = (summary: typeof summaryFilters[number]) => {
    setFilters((current) => ({ ...defaultSecurityNewsFilters(), kind: summary.kind, severity: summary.severity, exploitedOnly: summary.exploitedOnly, sort: current.sort }))
    setPage(0)
  }
  const showLoading = !data?.initialized && !query.isError && !failedSources.length
  const refreshError = query.refreshError instanceof RequestError && query.refreshError.status === 429
    ? '방금 업데이트를 요청했습니다. 잠시 후 다시 시도해 주세요.'
    : '업데이트 요청에 실패했습니다. 기존 자료를 유지합니다. 잠시 후 다시 시도해 주세요.'

  return (
    <div className="mx-auto w-full min-w-0 max-w-content space-y-5 3xl:max-w-none">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 text-caption font-medium text-brand-600"><ShieldCheck size={16} aria-hidden="true" />공개 보안 정보</div>
          <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">보안 뉴스</h1>
          <p className="mt-2 text-label text-apple-mid">CVE 취약점부터 보안 권고와 IT 보안 뉴스까지, 공개 보안 정보를 한곳에서 확인하세요.</p>
          <p className="mt-2 text-caption text-apple-light" aria-live="polite">{data?.refreshed_at ? `마지막 수집 시도 ${securityDateLabel(data.refreshed_at, true)} (KST)` : '공개 자료를 준비하고 있습니다.'}{query.refreshing ? ' · 업데이트 중' : ''}</p>
        </div>
        <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
          <button type="button" onClick={query.refresh} disabled={!query.canRefresh} className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50" aria-busy={query.refreshing}>
            <RefreshCw size={16} aria-hidden="true" className={query.refreshing ? 'animate-spin' : ''} />{query.refreshing ? '업데이트 중' : '최신 자료 확인'}
          </button>
          {!query.refreshing && query.retryAfterSeconds > 0 && <p className="text-caption text-apple-light">{Math.ceil(query.retryAfterSeconds / 60)}분 이내 다시 확인 가능</p>}
        </div>
      </header>

      <div role="group" aria-label="보안 정보 요약 필터" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {summaryFilters.map((metric) => {
          const selected = selectedSummary === metric.key
          const Icon = metric.icon
          return <button key={metric.key} type="button" onClick={() => selectSummary(metric)} aria-pressed={selected} aria-controls="security-news-results" className={`min-w-0 rounded-2xl border p-4 text-left shadow-apple-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-apple-bg md:p-5 ${selected ? 'border-brand-500 bg-brand-50' : 'border-apple-divider/60 bg-apple-surface hover:border-brand-400 hover:bg-apple-gray'}`}>
            <span className="flex items-center justify-between gap-2"><span className="break-keep text-caption font-medium text-apple-mid">{metric.label}</span><Icon size={18} className={`shrink-0 ${metric.color}`} aria-hidden="true" /></span>
            <span className="mt-3 flex items-center justify-between gap-2"><span className="text-page-title font-semibold tabular-nums text-apple-dark">{data?.initialized ? counts[metric.key].toLocaleString('ko-KR') : '—'}</span>{selected && <Check size={18} className="shrink-0 text-brand-600" aria-hidden="true" />}</span>
          </button>
        })}
      </div>
      <p className="text-caption text-apple-light">위젯을 선택하면 검색 조건을 초기화하고 해당 항목을 표시합니다. 집계는 현재 수집된 항목 기준이며 같은 CVE가 여러 출처에 포함될 수 있습니다. 실제 악용 여부는 CISA KEV 기준입니다.</p>

      <SecurityNewsSources sources={data?.sources ?? []} refreshing={query.refreshing} />
      <SecurityNewsTranslationControls language={language} onLanguageChange={setLanguage} translation={data?.translation} />
      {(query.isError || query.refreshError) && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-label text-amber-800">
        <p>{query.refreshError ? refreshError : data ? '최신 목록 조회에 실패했습니다. 마지막으로 받은 자료를 표시하며 자동으로 다시 확인합니다.' : '보안 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'}</p>
        {query.isError && <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching} className="rounded-lg px-2 py-1 font-semibold underline disabled:opacity-50">다시 조회</button>}
      </div>}
      {!!failedSources.length && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-label text-amber-800">{failedSources.map((source) => source.name).join(', ')} 수집이 원활하지 않습니다. 출처별 상태와 마지막 성공 시각을 확인해 주세요.</p>}

      <section aria-label="보안 정보 필터" className="rounded-2xl border border-apple-divider/70 bg-apple-surface p-4 md:p-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <label className="flex min-w-0 flex-col gap-2 text-caption font-medium text-apple-mid xl:col-span-2">검색
            <span className="relative"><Search size={16} className="pointer-events-none absolute left-3 top-3 text-apple-light" aria-hidden="true" /><input type="search" value={filters.search} onChange={(event) => update('search', event.target.value)} maxLength={200} placeholder="CVE 번호, 제품명, 제목 검색" className={`${fieldClass} pl-9`} /></span>
          </label>
          <label className="flex min-w-0 flex-col gap-2 text-caption font-medium text-apple-mid">출처<select value={filters.source} onChange={(event) => update('source', event.target.value)} className={fieldClass}><option value="">전체 출처</option>{data?.sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
          <label className="flex min-w-0 flex-col gap-2 text-caption font-medium text-apple-mid">위험도<select value={filters.severity} onChange={(event) => update('severity', event.target.value as SecurityNewsFilters['severity'])} className={fieldClass}><option value="all">전체 위험도</option><option value="high-risk">치명적 · 높은 위험도</option>{Object.entries(securitySeverityLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-control text-apple-mid">기간<select value={filters.days} onChange={(event) => update('days', event.target.value === 'all' ? 'all' : Number(event.target.value) as 7 | 30)} className={`${fieldClass} !w-auto`}><option value="all">전체 수집 기간</option><option value="7">최근 7일</option><option value="30">최근 30일</option></select></label>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-apple-divider px-3 py-2.5 text-control text-apple-dark"><input type="checkbox" checked={filters.exploitedOnly} onChange={(event) => update('exploitedOnly', event.target.checked)} className="h-4 w-4 accent-brand-600" />실제 악용 확인만</label>
          {hasFilters && <button type="button" onClick={reset} className={`${buttonClass} ml-auto`}><X size={14} aria-hidden="true" />필터 초기화</button>}
        </div>
        <p className="mt-3 text-caption text-apple-light">게시일 기준 · CISA KEV는 목록 등록일 기준 · 게시일이 없으면 수정일을 사용하며 날짜 미제공 항목은 전체 기간에만 표시합니다.</p>
      </section>

      <section id="security-news-results" aria-label="보안 정보 검색 결과" className="min-w-0 space-y-4" aria-busy={showLoading}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p role="status" className="text-control text-apple-mid">검색 결과 <strong className="font-semibold text-apple-dark">{filtered.length.toLocaleString('ko-KR')}</strong>개<span className="ml-2 text-caption text-apple-light">수집된 {counts.all.toLocaleString('ko-KR')}개 중</span></p>
          <label className="flex items-center gap-2 text-control text-apple-mid"><ArrowDownWideNarrow size={16} aria-hidden="true" /><span className="sr-only">정렬</span><select value={filters.sort} onChange={(event) => update('sort', event.target.value as SecurityNewsFilters['sort'])} className={`${fieldClass} !w-auto`}><option value="newest">최신순</option><option value="severity">위험도순</option></select></label>
        </div>
        {showLoading ? <div className="rounded-2xl border border-apple-divider bg-apple-surface py-8"><LoadingSpinner text="공개 보안 정보를 수집하고 있습니다..." /></div> : filtered.length ? (
          <div className="grid min-w-0 gap-4 lg:grid-cols-2 3xl:grid-cols-3">{filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map((item) => <SecurityNewsCard key={item.id} item={item} sourceName={sources.get(item.source_id) ?? item.source_id} language={language} />)}</div>
        ) : (
          <div className="rounded-2xl border border-apple-divider bg-apple-surface px-5 py-12 text-center">
            <SlidersHorizontal size={28} className="mx-auto text-apple-light" aria-hidden="true" />
            <h2 className="mt-4 text-section-title font-semibold text-apple-dark">{hasFilters ? '조건에 맞는 보안 정보가 없습니다' : failedSources.length || query.isError ? '수집 상태를 확인해 주세요' : '아직 수집된 보안 정보가 없습니다'}</h2>
            <p className="mt-2 text-label text-apple-mid">{hasFilters ? '검색어나 출처, 위험도, 기간을 조정해 보세요.' : '출처별 상태를 확인하거나 잠시 후 최신 자료를 다시 확인해 주세요.'}</p>
            {hasFilters && <button type="button" onClick={reset} className={`${buttonClass} mt-5`}>필터 초기화</button>}
          </div>
        )}
        {pageCount > 1 && <nav aria-label="보안 정보 페이지" className="flex items-center justify-center gap-4 py-2">
          <button type="button" className={buttonClass} aria-label="이전 페이지" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16} /></button>
          <span className="text-control tabular-nums text-apple-mid">{currentPage + 1} / {pageCount}</span>
          <button type="button" className={buttonClass} aria-label="다음 페이지" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}><ChevronRight size={16} /></button>
        </nav>}
      </section>
      <p className="pb-2 text-caption leading-relaxed text-apple-light">위험도 미평가는 낮은 위험을 의미하지 않습니다. 적용 대상과 조치 방법은 각 출처의 원문을 확인해 주세요. 원문 링크는 새 창에서 열립니다.</p>
    </div>
  )
}
