// frontend/src/presentation/components/cve/SolutionPackageResults.tsx
import { useId, useState } from 'react'
import { ChevronDown, RefreshCw, Search } from 'lucide-react'
import { cveReferenceUrl } from '@/application/services/securityNews'
import type { SolutionPackage } from '@/domain/SolutionPackages'
import { cveAction, CveCountFilter, CvePagination } from './CveResultControls'

const statusFilters = [
  { key: 'all', label: '전체', indicator: 'bg-brand-600' },
  { key: 'matched', label: 'CVE 매칭', indicator: 'bg-amber-500' },
  { key: 'unmatched', label: '미매칭', indicator: 'bg-blue-500' },
  { key: 'limited', label: '대조 제한', indicator: 'bg-apple-light' },
] as const
type StatusFilter = typeof statusFilters[number]['key']

const columns = 'md:grid-cols-[minmax(0,1.7fr)_minmax(0,0.85fr)_minmax(5.5rem,0.55fr)_minmax(0,1.45fr)]'
const field = 'min-w-0 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark focus:outline-brand-500'

function matchStatus(item: SolutionPackage) {
  if (item.cve_ids === null) return 'limited'
  return item.cve_ids.length > 0 ? 'matched' : 'unmatched'
}

function PackageRow({ item }: { item: SolutionPackage }) {
  const [expanded, setExpanded] = useState(false)
  const id = useId()
  const ids = item.cve_ids
  const packageLabel = `${item.name} ${item.version}`
  return <li aria-label={packageLabel} className={`grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-3 px-4 py-4 text-control md:px-5 ${columns}`}>
    <div className="col-span-full min-w-0 md:col-span-1">
      <strong className="break-all font-semibold text-apple-dark">{item.name}</strong>
      <span className="mt-1 block text-caption text-apple-mid">{item.category}</span>
    </div>
    <div className="min-w-0">
      <span className="mr-1 text-caption text-apple-mid md:hidden">확인 버전</span>
      <span className="break-all font-mono text-apple-dark">{item.version}</span>
    </div>
    <div>
      <span className="mr-1 text-caption text-apple-mid md:hidden">CVE</span>
      {ids && ids.length > 0 ? <button type="button" aria-label={`${packageLabel} CVE ${ids.length}건`}
        aria-expanded={expanded} aria-controls={expanded ? id : undefined} onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1 whitespace-nowrap rounded font-semibold text-brand-600 hover:underline focus-visible:outline-brand-500">
        {ids.length}건 <ChevronDown size={14} aria-hidden="true" className={expanded ? 'rotate-180' : undefined} />
      </button> : <span className="text-apple-mid">{ids === null ? '대조 제한' : '0건'}</span>}
      <span className="mt-1 block text-caption text-apple-mid">{item.cve_basis === 'advisory' ? '공식 권고' : '초기 인벤토리'}</span>
    </div>
    <div className="col-span-full min-w-0 md:col-span-1">
      <details className="text-caption md:hidden">
        <summary className="cursor-pointer font-medium text-brand-600">버전 확인 근거</summary>
        <p className="mt-1 break-words text-apple-mid">{item.evidence}</p>
      </details>
      <p className="hidden break-words leading-relaxed text-apple-mid md:block">{item.evidence}</p>
    </div>
    {expanded && ids && ids.length > 0 && <div id={id} role="region" aria-label={`${packageLabel} 매칭된 CVE`} tabIndex={0}
      className="col-span-full max-h-64 overflow-y-auto rounded-xl bg-apple-gray p-3 focus-visible:outline-brand-500">
      <ul className="flex flex-wrap gap-2">
        {ids.map((cve) => {
          const href = cveReferenceUrl(cve)
          return <li key={cve} className="rounded-md border border-apple-divider bg-apple-surface font-mono text-caption">
            {href ? <a href={href} target="_blank" rel="noopener noreferrer" aria-label={`${cve} NVD 상세`}
              className="block rounded-md px-2 py-1 font-semibold text-brand-600 hover:underline focus-visible:outline-brand-500">{cve}</a> :
              <span className="block px-2 py-1 text-apple-dark">{cve}</span>}
          </li>
        })}
      </ul>
    </div>}
  </li>
}

interface Props {
  packages: SolutionPackage[]
  description: string
  isFetching: boolean
  onRefresh: () => void
}

export default function SolutionPackageResults({ packages, description, isFetching, onRefresh }: Props) {
  const [status, setStatus] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = useState(1)
  const listId = useId()
  const titleId = useId()
  const categories = [...new Set(packages.map((item) => item.category))]
  const needle = search.trim().toLowerCase()
  const candidates = packages.filter((item) => (!category || item.category === category) &&
    (!needle || `${item.name} ${item.version}`.toLowerCase().includes(needle)))
  const counts = { all: candidates.length, matched: 0, unmatched: 0, limited: 0 }
  for (const item of candidates) counts[matchStatus(item)] += 1
  const matches = status === 'all' ? candidates : candidates.filter((item) => matchStatus(item) === status)
  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize))
  const currentPage = Math.min(page, pageCount)
  const start = (currentPage - 1) * pageSize

  return <section aria-labelledby={titleId} className="space-y-4">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <h2 id={titleId} className="text-section-title font-semibold text-apple-dark">포함 패키지
          <span className="ml-2 text-control font-semibold tabular-nums text-brand-600 sm:hidden">{matches.length.toLocaleString('ko-KR')}건</span>
        </h2>
        <p className="mt-1 hidden break-all font-mono text-caption text-apple-mid sm:block">{description}</p>
      </div>
      <button type="button" className={cveAction} disabled={isFetching} onClick={onRefresh}>
        <RefreshCw size={14} className={isFetching ? 'animate-spin' : undefined} aria-hidden="true" />다시 조회
      </button>
    </header>
    <div role="group" aria-label="패키지 CVE 대조 상태" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {statusFilters.map(({ key, label, indicator }) => <CveCountFilter key={key} label={label} indicator={indicator}
        count={counts[key]} controls={listId} selected={status === key} onClick={() => {
          setStatus(key)
          setPage(1)
        }} />)}
    </div>
    <div className="rounded-2xl border border-apple-divider bg-apple-surface shadow-apple-sm">
      <div className="flex flex-wrap items-center gap-3 p-4 md:px-5">
        <p role="status" className="mr-auto text-control text-apple-mid">검색 결과 <strong className="text-apple-dark">{matches.length.toLocaleString('ko-KR')}건</strong></p>
        <select aria-label="패키지 분류" className={`${field} w-full sm:w-auto`} value={category} onChange={(event) => {
          setCategory(event.target.value)
          setPage(1)
        }}>
          <option value="">전체 분류</option>
          {categories.map((name) => <option value={name} key={name}>{name}</option>)}
        </select>
        <div className="relative w-full sm:w-auto">
          <Search size={15} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-apple-mid" />
          <input type="search" aria-label="패키지명 또는 버전 검색" placeholder="패키지명 또는 버전 검색" className={`${field} w-full pl-9`}
            value={search} onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }} />
        </div>
      </div>
      <div id={listId} aria-busy={isFetching}>
        {matches.length > 0 ? <>
          <div aria-hidden="true" className={`hidden gap-4 border-y border-apple-divider bg-apple-gray px-5 py-2 text-caption font-medium text-apple-mid md:grid ${columns}`}>
            <span>패키지 · 분류</span><span>확인 버전</span><span>CVE</span><span>버전 확인 근거</span>
          </div>
          <ul aria-label="패키지 목록" className="divide-y divide-apple-divider/70">
            {matches.slice(start, start + pageSize).map((item) => <PackageRow key={item.id} item={item} />)}
          </ul>
        </> : <p className="border-t border-apple-divider px-5 py-8 text-center text-control text-apple-mid">검색 조건에 맞는 패키지가 없습니다.</p>}
      </div>
      <CvePagination page={currentPage} pageCount={pageCount} pageSize={pageSize} onPage={setPage} onPageSize={(size) => {
        setPageSize(size)
        setPage(1)
      }} label="패키지 목록 페이지" />
    </div>
  </section>
}
