// frontend/src/presentation/pages/SoftwareCvePage.tsx
import { useEffect, useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { SoftwareRelease, SoftwareSelection, SoftwareTarget } from '@/domain/SoftwareCve'
import type { SoftwareCveGateway } from '@/application/ports/ApplicationServices'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useCveSnapshot } from '@/presentation/hooks/useCveSnapshot'
import { usePersistentFilterState } from '@/presentation/hooks/usePersistentFilterState'
import { useAuthStore } from '@/presentation/state/authStore'
import { useReportStore } from '@/presentation/state/reportStore'
import CveCoveragePanel from '@/presentation/components/cve/CveCoveragePanel'
import CveFindings from '@/presentation/components/cve/CveFindings'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

interface Environment extends SoftwareSelection {
  series: string
}

const field = 'mt-2 block w-full min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:outline-brand-500'
const label = 'min-w-0 text-caption font-medium text-apple-mid'
const button = 'shrink-0 rounded-lg border border-apple-divider px-3 py-2 text-control font-medium text-brand-600 focus-visible:outline-brand-500 disabled:opacity-40'

type Scope = 'java' | 'db'

function releaseLabel(entry: SoftwareRelease) {
  const name = entry.label || entry.version
  return entry.supported === false ? `${name} · 지원 종료` : name
}

function SoftwareEnvironment({ scope, gateway, targets, target, env, save }: {
  scope: Scope; gateway: SoftwareCveGateway;
  targets: SoftwareTarget[]; target: SoftwareTarget; env: Environment; save: (selection: Environment) => void
}) {
  const java = scope === 'java'
  const releases = useCveSnapshot(scope, 'releases', { target: target.id }, (signal) => gateway.getReleases(target.id, signal))
  const options = releases.data?.versions ?? []
  const series = [...new Set(options.map((option) => option.series))].sort((a, b) => b.localeCompare(a, 'en', { numeric: true }))
  const shown = !env.series ? options : options.filter((option) => option.series === env.series)
  const selected = options.find((option) => option.version === env.version)
  const selectedLabel = selected ? releaseLabel(selected) : env.version
  const [editing, setEditing] = useState(false)
  const [manual, setManual] = useState(false)
  const [draft, setDraft] = useState(env.version)
  const id = useId()
  const custom = manual || (!!env.version && !!releases.data && !selected)
  const compact = !!env.version && !editing
  const zulu = target.id === 'zulu'
  const versionLabel = zulu ? '설치된 Zulu 빌드' : `설치된 ${target.label} 버전`
  const choose = (version: string) => {
    const release = options.find((option) => option.version === version)
    setEditing(false)
    save({ ...env, version, series: release ? env.series : '' })
  }

  return <>
    <section aria-label={java ? "Java 환경 선택" : "DB 환경 선택"} className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-apple-sm sm:p-5">
      {env.version && <div className={`min-w-0 sm:hidden ${editing ? 'mb-4 border-b border-apple-divider pb-3' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-semibold text-apple-dark">{target.label}</p>
            <p className="mt-1 break-words text-control text-apple-mid">{selectedLabel}</p>
          </div>
          <button type="button" className={button} aria-controls={id} aria-expanded={editing} onClick={() => setEditing(!editing)}>{editing ? '설정 닫기' : '환경 변경'}</button>
        </div>
        {compact && <details className="mt-2 text-caption text-apple-mid"><summary className="cursor-pointer">배포판 권고 수집 범위</summary><p className="mt-1">{target.coverage}</p></details>}
      </div>}
      <div id={id} className={compact ? 'hidden sm:block' : undefined}>
        <div className="grid items-start gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_0.65fr_1.6fr]">
          <fieldset className="min-w-0">
            <legend className={label}>{java ? 'JDK 배포판' : '데이터베이스'}</legend>
            <div className="mt-2 flex gap-1 rounded-xl border border-apple-divider bg-apple-gray p-1">
              {targets.map((item) => <button type="button" key={item.id} aria-pressed={item.id === target.id} disabled={!item.available}
                onClick={() => { if (item.id !== target.id) save({ target: item.id, series: '', version: '' }) }}
                className={`min-w-0 flex-1 rounded-lg px-2 py-1.5 text-control font-semibold focus-visible:outline-brand-500 ${item.id === target.id ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>
                {item.label}
              </button>)}
            </div>
          </fieldset>
          <label className={label}>{java ? 'Java 계열' : '버전 계열'}
            <select className={field} value={env.series} onChange={(event) => {
              setManual(false)
              setDraft('')
              save({ ...env, series: event.target.value, version: '' })
            }}>
              <option value="">전체 계열</option>
              {env.series && !series.includes(env.series) && <option value={env.series}>{java && 'Java '}{env.series}</option>}
              {series.map((value) => <option key={value} value={value}>{java && 'Java '}{value}</option>)}
            </select>
          </label>
          <div className="min-w-0 sm:col-span-2 lg:col-span-1">
            <label className={label}>{versionLabel}
              <select className={field} value={custom ? 'custom' : env.version} onChange={(event) => {
                const value = event.target.value
                setManual(value === 'custom')
                setDraft(value === 'custom' ? '' : value)
                if (value === 'custom') save({ target: target.id, version: '', series: '' })
                else choose(value)
              }}>
                <option value="">버전 선택</option>
                <option value="custom">직접 입력</option>
                {env.version && !custom && !selected && <option value={env.version}>{env.version}</option>}
                {shown.map((entry) => <option key={entry.version} value={entry.version}>{releaseLabel(entry)}</option>)}
              </select>
            </label>
            {custom && <form className="mt-2" onSubmit={(event) => { event.preventDefault(); if (draft.trim()) choose(draft.trim()) }}>
              <div className="flex min-w-0 items-center gap-2">
                <input aria-label={`${versionLabel} 직접 입력`} maxLength={128} required autoComplete="off" spellCheck={false} value={draft}
                  placeholder={zulu ? '예: Zulu11.58+23-CA' : java ? '예: 17.0.11 또는 8u402' : '서버의 제품 버전 입력'} className={`${field} !mt-0 font-mono`}
                  onChange={(event) => {
                    setManual(true)
                    setDraft(event.target.value)
                    if (env.version) save({ ...env, version: '' })
                  }} />
                <button className={button} type="submit" disabled={!draft.trim() || draft.trim() === env.version}>적용</button>
              </div>
              <p className="mt-2 text-caption text-apple-mid">{zulu ? <><code>java -version</code>에서 <code>Zulu</code> 뒤에 표시된 배포 빌드 번호를 입력하세요.</> :
                java ? <><code>java -version</code>에 표시된 OpenJDK 버전을 입력하세요.</> :
                <><code>{target.id === 'postgresql' ? 'SHOW server_version' : 'SELECT VERSION()'}</code>으로 확인한 서버의 제품 버전을 입력하세요.</>}</p>
            </form>}
          </div>
        </div>
        <p className="mt-4 text-control text-apple-mid">{target.coverage}</p>
      </div>
    </section>
    {(releases.isError || releases.data?.status === 'error') && <p role="alert" className="text-control text-apple-mid">버전 목록을 불러오지 못했습니다. <button type="button" className="font-semibold text-brand-600 underline" disabled={releases.isFetching} onClick={() => void releases.refetch()}>다시 조회</button></p>}
    {env.version ? <CveFindings key={env.version} scope={scope} selection={{ target: target.id, version: env.version }}
      read={gateway.getFindings} description={`${target.label} · ${selectedLabel}`} evidenceLabel="영향·수정 버전 · 공식 권고" /> :
      <>
        {releases.data && <CveCoveragePanel coverage={releases.data} />}
        <p role="status" className="rounded-2xl border border-apple-divider bg-apple-surface px-4 py-8 text-center text-control text-apple-mid">
          {releases.isPending ? '버전 목록을 불러오는 중입니다.' : '설치 버전을 선택하거나 직접 입력하면 해당 버전의 CVE를 조회합니다.'}
        </p>
      </>}
  </>
}

export default function SoftwareCvePage({ scope }: { scope: Scope }) {
  const services = useApplicationServices()
  const gateway = scope === 'java' ? services.javaCves : services.dbCves
  const title = scope === 'java' ? 'Java 취약점' : 'DB 취약점'
  const session = useAuthStore((state) => state.sessionVersion)
  const targets = useQuery({
    queryKey: [`${scope}-cves`, session, 'targets'], queryFn: ({ signal }) => gateway.getTargets(signal), staleTime: 300_000, retry: false,
  })
  const [saved, save] = usePersistentFilterState<Environment | null>(`${scope}-cves:environment:v1`, null)
  const target = targets.data?.find((item) => item.available && item.id === saved?.target) ?? targets.data?.find((item) => item.available)
  const validTarget = !!target && target.id === saved?.target
  const version = validTarget && typeof saved?.version === 'string' && saved.version.length <= 128 ? saved.version.trim() : ''
  const series = validTarget && typeof saved?.series === 'string' && saved.series.length <= 32 ? saved.series : ''
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  return <div className="mx-auto flex w-full min-w-0 max-w-content flex-col gap-3 sm:gap-5 3xl:max-w-none">
    <header className="flex flex-wrap items-baseline justify-between gap-2">
      <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">{title}</h1>
      <span className="text-caption text-apple-mid">매일 08:00 KST 공식 권고 자동 수집</span>
    </header>
    {target ? <SoftwareEnvironment key={`${scope}:${target.id}`} scope={scope} gateway={gateway} targets={targets.data ?? []} target={target} env={{ target: target.id, version, series }} save={save} /> :
      targets.isPending ? <LoadingSpinner text="지원 제품 목록을 불러오는 중입니다." /> : <p role="alert" className="text-control text-apple-mid">
        조회할 수 있는 제품이 없습니다. <button type="button" className="font-semibold text-brand-600 underline" onClick={() => void targets.refetch()}>다시 조회</button>
      </p>}
  </div>
}
