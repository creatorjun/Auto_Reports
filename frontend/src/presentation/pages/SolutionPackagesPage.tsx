// frontend/src/presentation/pages/SolutionPackagesPage.tsx
import { useEffect, useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { SolutionProduct } from '@/domain/SolutionPackages'
import SolutionPackageResults from '@/presentation/components/cve/SolutionPackageResults'
import { cveAction } from '@/presentation/components/cve/CveResultControls'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { useReportStore } from '@/presentation/state/reportStore'

const products: SolutionProduct[] = ['eyeCloudSIM', 'eyeCloudXoar', 'eyeCloudAI']
const versions: Record<SolutionProduct, string[]> = {
  eyeCloudSIM: ['3.1.0', '3.1.03'],
  eyeCloudXoar: ['4.0_R1', '4.0_R2', '4.0_R3'],
  eyeCloudAI: [],
}
interface Selection {
  product: SolutionProduct
  version: string | null
}

const panel = 'rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-apple-sm sm:p-5'
const label = 'min-w-0 text-caption font-medium text-apple-mid'

function SolutionEnvironment({ selection, onChange }: { selection: Selection; onChange: (next: Selection) => void }) {
  const [editing, setEditing] = useState(false)
  const editorId = useId()
  const { product, version } = selection
  return <section aria-label="솔루션 선택" className={panel}>
    <div className={`flex items-center justify-between gap-3 sm:hidden ${editing ? 'mb-4 border-b border-apple-divider pb-3' : ''}`}>
      <div className="min-w-0">
        <p className="font-semibold text-apple-dark">{product}</p>
        {version && <p className="mt-1 font-mono text-control text-apple-mid">{version}</p>}
      </div>
      <button type="button" aria-expanded={editing} aria-controls={editorId} onClick={() => setEditing(!editing)} className={cveAction}>
        {editing ? '설정 닫기' : '환경 변경'}
      </button>
    </div>
    <div id={editorId} className={editing ? undefined : 'hidden sm:block'}>
      <div className="grid items-start gap-4 sm:grid-cols-2">
        <fieldset className="min-w-0">
          <legend className={label}>솔루션 제품</legend>
          <div className="mt-2 flex flex-wrap gap-1 rounded-xl border border-apple-divider bg-apple-gray p-1">
            {products.map((item) => <button type="button" key={item} aria-pressed={item === product}
              onClick={() => {
                if (item !== product) onChange({ product: item, version: item === 'eyeCloudXoar' ? '4.0_R2' : versions[item][0] ?? null })
                if (item === 'eyeCloudAI') setEditing(false)
              }}
              className={`min-w-0 flex-1 rounded-lg px-1.5 py-1.5 text-control font-semibold focus-visible:outline-brand-500 ${item === product ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>
              {item}
            </button>)}
          </div>
        </fieldset>
        {version !== null && <label className={label}>제품 버전
          <select aria-label="제품 버전" value={version} onChange={(event) => {
            onChange({ product, version: event.target.value })
            setEditing(false)
          }} className="mt-2 block w-full min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:outline-brand-500">
            {versions[product].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>}
      </div>
    </div>
  </section>
}

export default function SolutionPackagesPage() {
  const [selection, setSelection] = useState<Selection>({ product: 'eyeCloudXoar', version: '4.0_R2' })
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
  const description = [product, version].filter(Boolean).join(' · ')
  const hasPackages = !!query.data?.packages.length
  const isR2 = product === 'eyeCloudXoar' && version === '4.0_R2'
  return <div className="mx-auto flex w-full min-w-0 max-w-content flex-col gap-3 sm:gap-5 3xl:max-w-none">
    <header className="flex flex-wrap items-baseline justify-between gap-2">
      <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">솔루션</h1>
      {isR2 && hasPackages && <span className="text-caption text-apple-mid">배포본 수집 <time dateTime="2026-11-06T11:47:00+09:00">2026-11-06 11:47 KST</time></span>}
    </header>
    <SolutionEnvironment selection={selection} onChange={setSelection} />
    {hasPackages && <details className="rounded-xl border border-apple-divider bg-apple-surface px-4 py-3 text-control text-apple-mid">
      <summary className="cursor-pointer font-semibold">패키지 버전과 CVE 대조 기준</summary>
      <p className="mt-2 leading-relaxed">배포 파일에서 버전을 확인한 패키지를 표시합니다. 미매칭은 수집 당시 일치하는 CVE가 0건인 경우이며, 대조 제한은 확인할 수 있는 취약점 범위가 제한된 경우입니다.</p>
    </details>}
    {query.isError && <p role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-control text-amber-800">
      {hasPackages ? '패키지 목록을 갱신하지 못했습니다. 마지막 조회 결과를 표시합니다.' : '패키지 목록을 불러오지 못했습니다.'}
      {!hasPackages && <button type="button" className="font-semibold underline" disabled={query.isFetching} onClick={() => void query.refetch()}>다시 조회</button>}
    </p>}
    {query.data && hasPackages ? <SolutionPackageResults key={description} packages={query.data.packages} description={description}
      isFetching={query.isFetching} onRefresh={() => void query.refetch()} /> :
      !query.isError && <p role="status" className="rounded-2xl border border-apple-divider bg-apple-surface px-4 py-8 text-center text-control text-apple-mid">
        {query.isPending ? '패키지 목록을 불러오는 중입니다.' : `${description}의 패키지 목록은 아직 등록되지 않았습니다.`}
      </p>}
  </div>
}
