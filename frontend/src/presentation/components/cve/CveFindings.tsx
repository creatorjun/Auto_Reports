// frontend/src/presentation/components/cve/CveFindings.tsx
import { useEffect, useState } from 'react'
import { ExternalLink, RefreshCw, Search } from 'lucide-react'
import type { CveFilters, CveFinding, CveFix, CveResults } from '@/domain/Cve'
import type { SecuritySeverity } from '@/domain/SecurityNews'
import { RequestError } from '@/application/errors/RequestError'
import { cveReferenceUrl, safeSecurityNewsUrl } from '@/application/services/securityNews'
import { useCveSnapshot } from '@/presentation/hooks/useCveSnapshot'
import { securityDateLabel, securitySeverityClasses, securitySeverityLabels } from '@/presentation/components/security/securityNewsFormatting'
import { cveAction, CveCountFilter, CvePagination } from './CveResultControls'
import CveCoveragePanel from './CveCoveragePanel'

const severities: SecuritySeverity[] = ['critical', 'high', 'medium', 'low', 'unknown']
const indicators: Record<SecuritySeverity, string> = { critical: 'bg-red-600', high: 'bg-amber-500', medium: 'bg-blue-500', low: 'bg-green-600', unknown: 'bg-apple-light' }

function Advisory({ fix, showFixedLabel }: { fix: CveFix; showFixedLabel: boolean }) {
  const href = safeSecurityNewsUrl(fix.advisory_url)
  const bounds = [
    fix.affected_from && `${fix.affected_from} ${fix.affected_from_inclusive === false ? '초과' : '이상'}`,
    fix.affected_through && `${fix.affected_through} ${fix.affected_through_inclusive === false ? '미만' : '이하'}`,
  ].filter(Boolean).join(' ~ ')
  return <div className="min-w-0">
    {bounds && <p className="break-words text-control text-apple-dark">영향 범위 · <strong>{bounds}</strong></p>}
    {fix.affected_version && <p className="break-words text-control text-apple-dark">영향 버전 · <strong>{fix.affected_version}</strong></p>}
    <span className="block break-all font-mono text-control font-medium text-apple-dark">{fix.fixed_version ? <>{showFixedLabel && '수정 버전 · '}{fix.fixed_version}</> : '수정 버전 미제공'}</span>
    {(fix.component || fix.channel || fix.series || fix.cvss_score != null) && <p className="mt-1 text-caption text-apple-mid">
      {[fix.component, fix.series && `${fix.series} 계열`, fix.channel, fix.cvss_score != null ? `CVSS ${fix.cvss_score.toFixed(1)}` : null].filter(Boolean).join(' · ')}
    </p>}
    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-apple-mid">
      {href ? <a href={href} target="_blank" rel="noopener noreferrer" title={fix.title ?? undefined} className="inline-flex items-center gap-1 rounded text-brand-600 hover:underline">{fix.advisory_id}<ExternalLink size={12} aria-hidden="true" /></a> : <span>{fix.advisory_id}</span>}
      {fix.issued_at && <time dateTime={fix.issued_at}>{securityDateLabel(fix.issued_at)}</time>}
    </div>
  </div>
}

function FindingRow({ item, evidenceLabel, showFixedLabel }: { item: CveFinding; evidenceLabel: string; showFixedLabel: boolean }) {
  const href = cveReferenceUrl(item.cve_id)
  const [first, ...additional] = item.fixes
  return <li className="grid gap-x-4 gap-y-3 px-4 py-4 text-control md:grid-cols-[minmax(10rem,0.8fr)_minmax(0,1.5fr)_minmax(12rem,1fr)] md:px-5">
    <div className="flex flex-wrap items-center justify-between gap-2 md:flex-col md:items-start md:justify-start">
      {href ? <a href={href} target="_blank" rel="noopener noreferrer" className="rounded font-mono font-semibold text-brand-600 hover:underline" aria-label={`${item.cve_id} NVD 상세`}>{item.cve_id}</a> : <strong>{item.cve_id}</strong>}
      <span className={securitySeverityClasses[item.severity]}>{securitySeverityLabels[item.severity]}</span>
    </div>
    <div className="min-w-0">
      {item.summary ? <p className="break-words leading-relaxed text-apple-dark">{item.summary}</p> : first?.title ?
        <p className="break-words leading-relaxed text-apple-dark"><span className="mr-1 text-caption font-medium text-apple-mid">권고 제목</span>{first.title}</p> :
        <span className="text-apple-mid">CVE 설명 미제공</span>}
    </div>
    <div className="min-w-0"><span className="mb-1 block text-caption text-apple-mid md:hidden">{evidenceLabel}</span>
      {first ? <Advisory fix={first} showFixedLabel={showFixedLabel} /> : <span className="text-apple-mid">수정 정보 미제공</span>}
      {additional.length > 0 && <details className="mt-2">
        <summary className="cursor-pointer text-caption font-medium text-brand-600">다른 권고 근거 {additional.length.toLocaleString('ko-KR')}개</summary>
        <div className="mt-2 space-y-2 border-l border-apple-divider pl-3">{additional.map((fix, index) => <Advisory key={`${fix.advisory_id}-${index}`} fix={fix} showFixedLabel={showFixedLabel} />)}</div>
      </details>}
    </div>
  </li>
}

interface Props<S extends { version: string }> {
  scope: 'kernel' | 'java' | 'db'
  selection: S
  description: string
  evidenceLabel: string
  read: (request: S & CveFilters, signal: AbortSignal) => Promise<CveResults>
}

export default function CveFindings<S extends { version: string }>({ scope, selection, description, evidenceLabel, read }: Props<S>) {
  const [filters, setFilters] = useState<CveFilters>({ severity: 'all', search: '', page: 1, page_size: 25 })
  const [search, setSearch] = useState('')
  const request = { ...selection, ...filters }
  const query = useCveSnapshot(scope, 'findings', request, (signal) => read(request, signal))
  const headingId = `${scope}-findings-title`
  const listId = `${scope}-cve-list`
  const results = query.data
  const total = results?.total ?? null
  const hasData = total !== null
  const pageCount = hasData && results ? Math.max(1, Math.ceil(total / results.page_size)) : 1
  useEffect(() => {
    if (hasData && filters.page > pageCount) setFilters((prev) => ({ ...prev, page: pageCount }))
  }, [hasData, filters.page, pageCount])
  const counts = results?.severity_counts
  const totalAcrossSeverities = counts && severities.reduce((sum, key) => sum + (counts[key] ?? 0), 0)
  const errorText = query.error instanceof RequestError && query.error.status === 422
    ? typeof query.error.detail === 'string' ? query.error.detail : '선택한 배포판의 설치 버전을 확인하세요.'
    : 'CVE 조회에 실패했습니다. 잠시 후 다시 조회하세요.'

  return <>
    {results && <CveCoveragePanel coverage={results} />}
    <section aria-labelledby={headingId} className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 id={headingId} className="text-section-title font-semibold text-apple-dark">{scope === 'kernel' ? '영향받는 CVE' : '버전 기준 CVE'}{total !== null && <span className="ml-2 text-control font-semibold tabular-nums text-brand-600 sm:hidden">
            {(filters.search || filters.severity !== 'all') && '필터 결과 '}{total.toLocaleString('ko-KR')}건
          </span>}</h2>
          <p className="mt-1 hidden break-all font-mono text-caption text-apple-mid sm:block">{description}</p>
        </div>
        <button type="button" className={cveAction} disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={14} className={query.isFetching ? 'animate-spin' : ''} aria-hidden="true" />다시 조회</button>
      </header>
      {query.isError && <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-control text-amber-800">{errorText}{hasData && ' 마지막 조회 결과를 표시합니다.'}</p>}
      <div role="group" aria-label="검색 조건별 위험도 필터" className="grid grid-cols-3 gap-2 lg:grid-cols-6">
        {(['all', ...severities] as const).map((key) => {
          const selected = filters.severity === key
          const count = key === 'all' ? totalAcrossSeverities : counts?.[key]
          return <CveCountFilter key={key} controls={listId} selected={selected}
            label={key === 'all' ? '전체' : securitySeverityLabels[key]} count={hasData ? count ?? null : null}
            indicator={key === 'all' ? 'bg-brand-600' : indicators[key]}
            onClick={() => setFilters((prev) => ({ ...prev, severity: key, page: 1 }))} />
        })}
      </div>
      <div className="rounded-2xl border border-apple-divider bg-apple-surface shadow-apple-sm">
        <form className="flex flex-wrap items-center justify-between gap-3 p-4 md:px-5" onSubmit={(event) => { event.preventDefault(); setFilters((prev) => ({ ...prev, search: search.trim(), page: 1 })) }}>
          <p role="status" className="text-control text-apple-mid">{hasData ? <>검색 결과 <strong className="text-apple-dark">{total.toLocaleString('ko-KR')}건</strong></> : query.isFetching ? 'CVE 조회 중' : '결과 미확인'}</p>
          <div className="flex w-full min-w-0 gap-2 sm:w-auto"><input type="search" aria-label="CVE 번호 검색" placeholder="CVE 번호 검색" value={search} maxLength={100} onChange={(event) => {
            const value = event.target.value
            setSearch(value)
            if (!value) setFilters((prev) => ({ ...prev, search: '', page: 1 }))
          }} className="min-w-0 flex-1 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark focus:outline-brand-500" />
          <button type="submit" className={cveAction}><Search size={14} aria-hidden="true" />검색</button></div>
        </form>
        <div id={listId} aria-busy={query.isFetching}>
          {results && results.items.length > 0 ? <>
            <div aria-hidden="true" className="hidden gap-4 border-y border-apple-divider bg-apple-gray px-5 py-2 text-caption font-medium text-apple-mid md:grid md:grid-cols-[minmax(10rem,0.8fr)_minmax(0,1.5fr)_minmax(12rem,1fr)]"><span>CVE · 위험도</span><span>취약점 설명</span><span>{evidenceLabel}</span></div>
            <ul className="divide-y divide-apple-divider/70">{results.items.map((item) => <FindingRow key={item.cve_id} item={item} evidenceLabel={evidenceLabel} showFixedLabel={scope !== 'kernel'} />)}</ul>
          </> : <p className="border-t border-apple-divider px-5 py-8 text-center text-control text-apple-mid">
            {query.isFetching && !hasData ? '공식 권고를 확인 중입니다.' : hasData && results?.status === 'ready' && !query.isError ? '수집된 공식 권고 중 선택한 조건에 해당하는 CVE가 없습니다.' :
              '현재 자료로는 선택한 조건의 CVE를 확인할 수 없습니다.'}
          </p>}
        </div>
        {hasData && <CvePagination label="CVE 검색 결과 페이지" page={filters.page} pageCount={pageCount} pageSize={filters.page_size}
          onPage={(page) => setFilters((prev) => ({ ...prev, page }))}
          onPageSize={(page_size) => setFilters((prev) => ({ ...prev, page_size, page: 1 }))} />}
      </div>
    </section>
  </>
}
