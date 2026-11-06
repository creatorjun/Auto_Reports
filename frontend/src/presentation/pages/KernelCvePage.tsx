// frontend/src/presentation/pages/KernelCvePage.tsx
import { useEffect, useId, useState } from 'react'
import type { FormEvent } from 'react'
import type { KernelSelection, KernelTarget } from '@/domain/KernelCve'
import { resolveKernelSelection } from '@/application/services/kernelSelection'
import { useKernelReleases, useKernelTargets } from '@/presentation/hooks/useKernelCves'
import { usePersistentFilterState } from '@/presentation/hooks/usePersistentFilterState'
import { useReportStore } from '@/presentation/state/reportStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import CveCoveragePanel from '@/presentation/components/cve/CveCoveragePanel'
import CveFindings from '@/presentation/components/cve/CveFindings'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import UpstreamKernelCves from '@/presentation/components/kernel-cves/UpstreamKernelCves'

const field = 'mt-2 block w-full min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-400/30'
const label = 'min-w-0 text-caption font-medium text-apple-mid'

function KernelVersionField({ versions, version, onChange }: { versions: string[]; version: string; onChange: (version: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(version)
  const custom = editing || (!!version && versions.length > 0 && !versions.includes(version))
  const apply = (event: FormEvent) => {
    event.preventDefault()
    const next = draft.trim()
    if (next) onChange(next)
  }
  return <div className="min-w-0">
    <label className={label}>설치된 커널 버전
      <select className={field} value={custom ? 'custom' : version} onChange={(event) => {
        const value = event.target.value
        setEditing(value === 'custom')
        setDraft(value === 'custom' ? '' : value)
        onChange(value === 'custom' ? '' : value)
      }}>
        <option value="">버전 선택</option>
        <option value="custom">직접 입력</option>
        {version && !versions.includes(version) && !custom && <option value={version}>{version}</option>}
        {versions.map((value) => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
    {custom && <form onSubmit={apply} className="mt-2 flex items-center gap-2">
      <input aria-label="커널 버전 직접 입력" autoComplete="off" spellCheck={false} maxLength={128} required placeholder="uname -r 출력값" className={`${field} !mt-0 font-mono`} value={draft} onChange={(event) => {
        setEditing(true)
        setDraft(event.target.value)
        if (version) onChange('')
      }} />
      <button type="submit" disabled={!draft.trim() || version === draft.trim()} className="shrink-0 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-semibold text-white hover:bg-brand-700 disabled:opacity-40">적용</button>
    </form>}
  </div>
}

function KernelEnvironment({ targets, target, selection, save }: {
  targets: KernelTarget[]; target: KernelTarget; selection: KernelSelection; save: (selection: KernelSelection) => void
}) {
  const { target: id, package: pkg, architecture, version } = selection
  const { kernelCves } = useApplicationServices()
  const [editing, setEditing] = useState(false)
  const editorId = useId()
  const compact = !!version && !editing
  const build = { target: id, package: pkg, architecture }
  const releases = useKernelReleases(build)
  return <>
    <section aria-label="커널 환경 선택" className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-apple-sm sm:p-5">
      {version && <div className={`min-w-0 sm:hidden ${editing ? 'mb-4 border-b border-apple-divider pb-3' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-label font-semibold text-apple-dark">{target.label}</p>
            <p className="mt-0.5 break-all font-mono text-caption text-apple-mid">{pkg} · {architecture}</p>
          </div>
          <button type="button" aria-controls={editorId} aria-expanded={editing} onClick={() => setEditing(!editing)} className="shrink-0 rounded-lg border border-apple-divider px-3 py-2 text-control font-medium text-brand-600 focus-visible:outline-brand-500">
            {editing ? '설정 닫기' : '환경 변경'}
          </button>
        </div>
        <p className="mt-2 break-all font-mono text-control font-medium text-apple-dark">{version}</p>
        {compact && target.coverage && <details className="mt-2 text-caption text-apple-mid">
          <summary className="cursor-pointer">배포판 권고 수집 범위</summary>
          <p className="mt-1">{target.coverage}</p>
        </details>}
      </div>}
      <div id={editorId} className={compact ? 'hidden sm:block' : undefined}>
      <div className="grid items-start gap-4 sm:grid-cols-2 xl:grid-cols-[1.15fr_1fr_0.8fr_1.5fr]">
        <label className={label}>OS 배포판 · 버전
          <select className={field} value={id} onChange={(event) => {
            const next = resolveKernelSelection(targets, { target: event.target.value })
            if (next) save(next)
          }}>
            {targets.filter((item) => item.available).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <label className={label}>커널 패키지
          <select className={field} value={pkg} onChange={(event) => save({ ...selection, package: event.target.value, version: '' })}>
            {target.packages.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <label className={label}>아키텍처
          <select className={field} value={architecture} onChange={(event) => save({ ...selection, architecture: event.target.value, version: '' })}>
            {target.architectures.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <KernelVersionField versions={releases.data?.versions ?? []} version={version} onChange={(next) => {
          if (next) setEditing(false)
          save({ ...selection, version: next })
        }} />
      </div>
      {target.coverage && <p className="mt-4 text-control text-apple-mid">{target.coverage}</p>}
      </div>
    </section>
    {(releases.isError || releases.data?.status === 'error' || releases.data?.status === 'stale' || releases.data?.status === 'partial') &&
      <div role="status" className="flex flex-wrap items-center gap-2 text-control text-apple-mid">
        {releases.isError ? '커널 버전 목록 조회에 실패했습니다.' : '커널 버전 목록의 수집 상태를 확인하세요.'}
        <button type="button" className="font-semibold text-brand-600 underline" disabled={releases.isFetching} onClick={() => void releases.refetch()}>버전 목록 다시 조회</button>
      </div>}
    {version ? <CveFindings key={version} scope="kernel" selection={selection} read={kernelCves.getFindings} description={`${pkg} · ${version} · ${architecture}`} evidenceLabel="수정 버전 · 공식 권고" /> : <>
      {releases.data && <CveCoveragePanel coverage={releases.data} />}
      <p role="status" className="rounded-2xl border border-apple-divider bg-apple-surface px-5 py-10 text-center text-control text-apple-mid">
        {releases.isPending ? '커널 버전 목록을 불러오는 중입니다.' : '설치된 커널 버전을 선택하거나 직접 입력하면 해당 빌드에 영향을 주는 CVE를 확인할 수 있습니다.'}
      </p>
    </>}
    <UpstreamKernelCves target={id} />
  </>
}

export default function KernelCvePage() {
  const targets = useKernelTargets()
  const [saved, setSaved] = usePersistentFilterState<KernelSelection | null>('kernel-cves:selection:v1', null)
  const selection = resolveKernelSelection(targets.data ?? [], saved)
  const target = targets.data?.find((item) => item.id === selection?.target)
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  return <div className="mx-auto flex w-full min-w-0 max-w-content flex-col gap-3 sm:gap-5 3xl:max-w-none">
    <header>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">OS 커널 취약점</h1>
        <span className="text-caption text-apple-mid">매일 08:00 KST 공식 권고 자동 수집</span>
      </div>
      <p className={`mt-1 text-control text-apple-mid ${selection?.version ? 'hidden sm:block' : ''}`}>배포판의 보안 권고에서 설치된 커널 버전에 해당하는 CVE와 수정 버전을 확인합니다.</p>
    </header>
    {targets.isPending ? <LoadingSpinner text="지원 배포판을 불러오는 중입니다." /> :
      targets.isError && !targets.data ? <p role="alert" className="text-control text-apple-mid">배포판 목록을 불러오지 못했습니다. <button className="font-semibold text-brand-600 underline" onClick={() => void targets.refetch()}>다시 조회</button></p> :
      target && selection ? <KernelEnvironment key={JSON.stringify([target.id, selection.package, selection.architecture])} targets={targets.data ?? []} target={target} selection={selection} save={setSaved} /> :
      <p role="status" className="text-control text-apple-mid">조회할 수 있는 배포판이 없습니다.</p>}
  </div>
}
