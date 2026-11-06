// frontend/src/presentation/pages/SolutionPackagesPage.tsx
import { useEffect, useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import type { SolutionPackage, SolutionProduct } from '@/domain/SolutionPackages'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { useReportStore } from '@/presentation/state/reportStore'

const products: SolutionProduct[] = ['eyeCloudSIM', 'eyeCloudXoar', 'eyeCloudAI']
const versions: Record<SolutionProduct, string[]> = {
  eyeCloudSIM: ['3.1.0', '3.1.03'],
  eyeCloudXoar: ['4.0_R1', '4.0_R2', '4.0_R3'],
  eyeCloudAI: [],
}
const pageSize = 25
const panel = 'rounded-2xl border border-apple-divider bg-apple-surface shadow-apple-sm'
const field = 'w-full min-w-0 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark focus-visible:outline-brand-500'
const pageButton = 'rounded-lg border border-apple-divider p-2 text-apple-dark hover:bg-apple-gray focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-40'

function PackageRow({ item }: { item: SolutionPackage }) {
  const [expanded, setExpanded] = useState(false)
  const listId = useId()
  const ids = item.cve_ids
  return <>
    <tr className="align-top">
      <td className="px-3 py-3 sm:px-5">
        <span className="break-all font-medium text-apple-dark">{item.name}</span>
        <span className="mt-1 block text-caption text-apple-mid">{item.category}</span>
        <details className="mt-1 text-caption md:hidden">
          <summary className="cursor-pointer text-brand-600">버전 확인 근거</summary>
          <p className="mt-1 break-words text-apple-mid">{item.evidence}</p>
        </details>
      </td>
      <td className="break-all px-2 py-3 font-mono text-apple-dark sm:px-3">{item.version}</td>
      <td className="hidden break-words px-4 py-3 text-apple-mid md:table-cell">{item.evidence}</td>
      <td className="px-2 py-3 text-apple-mid sm:px-3">
        {ids?.length ? <button type="button" aria-label={`${item.name} ${item.version} CVE ${ids.length}건`} aria-expanded={expanded}
          aria-controls={expanded ? listId : undefined} onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 whitespace-nowrap rounded text-control font-semibold text-brand-600 hover:underline focus-visible:outline-brand-500">
          {ids.length}건 <ChevronDown size={14} aria-hidden="true" className={expanded ? 'rotate-180' : undefined} />
        </button> : ids ? '0건' : '대조 제한'}
      </td>
    </tr>
    {expanded && ids && ids.length > 0 && <tr>
      <td colSpan={4} className="bg-apple-gray px-3 py-3 sm:px-5">
        <div id={listId} role="region" aria-label={`${item.name} ${item.version} 매칭된 CVE`} tabIndex={0}
          className="max-h-64 overflow-y-auto rounded focus-visible:outline-brand-500">
          <ul className="flex flex-wrap gap-2">
            {ids.map((id) => <li key={id} className="rounded-md border border-apple-divider bg-apple-surface px-2 py-1 font-mono text-caption text-apple-dark">{id}</li>)}
          </ul>
        </div>
      </td>
    </tr>}
  </>
}

function PackageTable({ packages, collectedAt }: { packages: SolutionPackage[]; collectedAt?: string }) {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const needle = search.trim().toLowerCase()
  const categories = [...new Set(packages.map((item) => item.category))]
  const matches = packages.filter((item) => (!category || item.category === category) &&
    (!needle || `${item.name} ${item.version}`.toLowerCase().includes(needle)))
  const pages = Math.max(1, Math.ceil(matches.length / pageSize))
  const currentPage = Math.min(page, pages)
  const start = (currentPage - 1) * pageSize

  return <div className={panel}>
    <div className="flex flex-wrap items-center gap-3 p-4 sm:px-5">
      <p role="status" className="mr-auto whitespace-nowrap text-control text-apple-mid">
        {needle || category ? '검색 결과' : '버전 확인'} <strong className="tabular-nums text-apple-dark">{matches.length.toLocaleString('ko-KR')}건</strong>
      </p>
      <select aria-label="패키지 분류" className={`${field} sm:w-auto`} value={category} onChange={(event) => {
        setCategory(event.target.value)
        setPage(1)
      }}>
        <option value="">전체 분류</option>
        {categories.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <div className="relative w-full sm:w-auto">
        <Search size={15} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-apple-mid" />
        <input type="search" aria-label="패키지명 또는 버전 검색" placeholder="패키지명 또는 버전 검색" className={`${field} pl-9`} value={search} onChange={(event) => {
          setSearch(event.target.value)
          setPage(1)
        }} />
      </div>
    </div>
    <p className="px-4 pb-3 text-caption text-apple-mid sm:px-5">
      CVE는 배포본 수집 당시{collectedAt && `(${collectedAt})`}의 대조 결과이며, 0건은 당시 미매칭을 뜻합니다.
    </p>
    {matches.length > 0 ? <table className="w-full table-fixed border-collapse text-left text-control">
      <caption className="sr-only">배포본에 포함된 패키지와 확인 버전</caption>
      <thead className="border-y border-apple-divider bg-apple-gray text-caption text-apple-mid">
        <tr>
          <th scope="col" className="w-1/2 px-3 py-2 font-medium sm:px-5 md:w-[36%]">패키지</th>
          <th scope="col" className="w-1/4 px-2 py-2 font-medium sm:px-3 md:w-[18%]">확인 버전</th>
          <th scope="col" className="hidden w-[32%] px-4 py-2 font-medium md:table-cell">버전 확인 근거</th>
          <th scope="col" className="w-1/4 px-2 py-2 font-medium sm:px-3 md:w-[14%]">CVE</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-apple-divider">
        {matches.slice(start, start + pageSize).map((item) => <PackageRow key={item.id} item={item} />)}
      </tbody>
    </table> : <p className="border-t border-apple-divider px-4 py-8 text-center text-control text-apple-mid">검색 조건에 맞는 패키지가 없습니다.</p>}
    {pages > 1 && <nav aria-label="패키지 목록 페이지" className="flex items-center justify-end gap-3 border-t border-apple-divider px-4 py-3 sm:px-5">
      <button type="button" aria-label="이전 페이지" className={pageButton} disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16} aria-hidden="true" /></button>
      <span className="text-control tabular-nums text-apple-mid">{currentPage} / {pages}</span>
      <button type="button" aria-label="다음 페이지" className={pageButton} disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}><ChevronRight size={16} aria-hidden="true" /></button>
    </nav>}
  </div>
}

export default function SolutionPackagesPage() {
  const [selection, setSelection] = useState<{ product: SolutionProduct; version: string | null }>({
    product: 'eyeCloudXoar', version: '4.0_R2',
  })
  const { product, version } = selection
  const { solutionPackages } = useApplicationServices()
  const session = useAuthStore((state) => state.sessionVersion)
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  const query = useQuery({
    queryKey: ['solution-packages', session, product, version],
    queryFn: ({ signal }) => solutionPackages.list(product, version, signal),
    retry: false,
  })
  const selectedLabel = [product, version].filter(Boolean).join(' ')

  return <div className="mx-auto flex w-full min-w-0 max-w-content flex-col gap-4 sm:gap-5 3xl:max-w-none">
    <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">솔루션</h1>
    <section aria-label="솔루션 선택" className={`${panel} grid gap-4 p-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] sm:p-5`}>
      <fieldset className="min-w-0">
        <legend className="text-caption font-medium text-apple-mid">제품</legend>
        <div className="mt-2 flex flex-wrap gap-1 rounded-xl border border-apple-divider bg-apple-gray p-1">
          {products.map((item) => <button type="button" key={item} aria-pressed={product === item}
            onClick={() => { if (item !== product) setSelection({ product: item, version: item === 'eyeCloudXoar' ? '4.0_R2' : versions[item][0] ?? null }) }}
            className={`flex-1 rounded-lg px-2 py-1.5 text-control font-semibold focus-visible:outline-brand-500 ${product === item ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>
            {item}
          </button>)}
        </div>
      </fieldset>
      {versions[product].length > 0 && <label className="text-caption font-medium text-apple-mid">제품 버전
        <select aria-label="제품 버전" className={`${field} mt-2 block`} value={version ?? ''} onChange={(event) => setSelection({ product, version: event.target.value })}>
          {versions[product].map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>}
    </section>
    <section aria-labelledby="solution-packages-title" className="space-y-3">
      <h2 id="solution-packages-title" className="text-section-title font-semibold text-apple-dark">포함 패키지 <span className="ml-1 inline-block font-mono text-caption font-medium text-apple-mid">{selectedLabel}</span></h2>
      {query.isPending ? <p role="status" className={`${panel} p-8 text-center text-control text-apple-mid`}>패키지 목록을 불러오는 중입니다.</p>
        : query.isError ? <div role="alert" className={`${panel} flex flex-wrap items-center justify-center gap-3 p-8 text-control text-apple-mid`}>
          패키지 목록을 불러오지 못했습니다.
          <button type="button" className="font-semibold text-brand-600 underline" disabled={query.isFetching} onClick={() => void query.refetch()}>다시 조회</button>
        </div>
        : query.data.packages.length > 0 ? <PackageTable key={selectedLabel} packages={query.data.packages}
          collectedAt={product === 'eyeCloudXoar' && version === '4.0_R2' ? '2026-11-06 11:47 KST' : undefined} />
        : <p role="status" className={`${panel} p-8 text-center text-control text-apple-mid`}>{selectedLabel}의 패키지 목록은 아직 등록되지 않았습니다.</p>}
    </section>
  </div>
}
