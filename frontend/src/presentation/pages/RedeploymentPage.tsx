// frontend/src/presentation/pages/RedeploymentPage.tsx
import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Clock3, Loader2, RotateCcw } from 'lucide-react'
import type { RedeploymentScope } from '@/domain/RedeploymentReport'
import { filterRedeployments, redeploymentIsStale, redeploymentMonths, redeploymentSummary } from '@/application/services/redeploymentReport'
import { RequestError } from '@/application/errors/RequestError'
import { useRedeployments, useRefreshRedeployments } from '@/presentation/hooks/useRedeployments'
import { useReportStore } from '@/presentation/state/reportStore'
import { CATEGORICAL_CHART_COLORS } from '@/presentation/config/constants'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import RedeploymentTickets from '@/presentation/components/redeployments/RedeploymentTickets'

const scopeLabels = { all: '전체', active: '진행 중', closed: '완료' } as const

export default function RedeploymentPage() {
  const query = useRedeployments()
  const refresh = useRefreshRedeployments()
  const report = query.data
  const [scope, setScope] = useState<RedeploymentScope>('all')
  const [cause, setCause] = useState('')
  const [search, setSearch] = useState('')
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  const summary = useMemo(() => redeploymentSummary(report?.tickets ?? []), [report])
  const scoped = useMemo(() => filterRedeployments(report?.tickets ?? [], scope, '', ''), [report, scope])
  const causes = useMemo(() => redeploymentSummary(scoped).causes, [scoped])
  const tickets = useMemo(() => filterRedeployments(scoped, 'all', cause, search), [scoped, cause, search])
  const monthly = useMemo(() => report ? redeploymentMonths(report) : { months: [], unassigned: 0 }, [report])
  const maximum = Math.max(1, ...monthly.months.map((item) => item.count))
  const error = refresh.error ?? query.error
  const formattedDate = report ? new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Seoul' }).format(new Date(report.generated_at)) : ''
  const changeScope = (value: RedeploymentScope) => { setScope(value); setCause('') }

  return <div className="mx-auto flex w-full max-w-content flex-col gap-5 break-keep 3xl:max-w-none">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="mb-2 flex items-center gap-2 text-caption font-medium text-brand-600"><RotateCcw size={16} />재배포 현황 보고서</div><h1 className="text-page-title font-semibold tracking-tight text-apple-dark">재배포 현황</h1><p className="mt-2 text-label text-apple-mid">2026년 1월 1일 이후 완료 현황과 현재 진행 중인 재배포의 원인을 확인합니다.</p></div>
      <button type="button" disabled={refresh.isPending} onClick={() => refresh.mutate()} className="flex min-h-11 items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-medium text-white hover:bg-brand-700 disabled:opacity-50">{refresh.isPending ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}{refresh.isPending ? '갱신 중' : '지금 갱신'}</button>
    </header>
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-apple-divider bg-apple-surface px-4 py-3 text-caption text-apple-mid"><span className="flex items-center gap-2"><Clock3 size={16} className="text-brand-600" />매일 08:00 자동 갱신 · KST</span><span>{report ? `마지막 갱신 ${formattedDate} KST` : '첫 보고서 생성 대기 중'}</span></div>
    {refresh.isPending && <p role="status" className="text-label text-apple-mid">Jira에서 최신 재배포 정보를 수집하고 저장하고 있습니다.</p>}
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-label text-red-700">{error instanceof RequestError && typeof error.detail === 'string' ? error.detail : '보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'}<button onClick={() => void query.refetch()} className="ml-3 underline">다시 불러오기</button></div>}
    {report && redeploymentIsStale(report.generated_at) && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-caption text-amber-800">오늘 정기 갱신 시각 이후의 보고서가 아직 없습니다. 마지막으로 저장된 데이터를 표시합니다. 잠시 후 확인하거나 ‘지금 갱신’을 눌러 주세요.</p>}
    {query.isLoading && <LoadingSpinner text="마지막 재배포 보고서를 불러오는 중..." />}
    {!query.isLoading && !report && !query.isError && <div className="card py-14 text-center"><RotateCcw size={32} className="mx-auto mb-3 text-brand-600" /><h2 className="text-section-title font-semibold text-apple-dark">첫 재배포 보고서를 준비하고 있습니다.</h2><p className="mt-2 text-label text-apple-mid">자동 생성이 끝나면 표시됩니다. ‘지금 갱신’으로 직접 생성할 수도 있습니다.</p></div>}
    {report && <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {([
          ['all', '재배포 티켓', summary.total, '완료 + 현재 진행 중'],
          ['closed', '완료', summary.closed, '2026-01-01 이후 해결된 티켓'],
          ['active', '진행 중', summary.active, '현재 재배포 Y · 생성일 제한 없음'],
        ] as const).map(([value, label, count, note]) => <button key={value} onClick={() => changeScope(value)} aria-pressed={scope === value} className={`card text-left transition-shadow hover:shadow-md ${scope === value ? 'ring-2 ring-brand-400' : ''}`}><p className="flex items-center gap-2 text-label font-semibold text-apple-dark">{value === 'closed' ? <CheckCircle2 size={18} className="text-green-600" /> : <RotateCcw size={18} className="text-brand-600" />}{label}</p><p className="mt-3 text-metric-compact font-semibold tabular-nums text-apple-dark">{count}<span className="ml-2 text-label font-medium text-apple-mid">건</span></p><p className="mt-2 text-caption text-apple-mid">{note}</p></button>)}
        <div className="card"><p className="text-label font-semibold text-apple-dark">기록된 재패치 횟수</p><p className="mt-3 text-metric-compact font-semibold tabular-nums text-apple-dark">{summary.repatches}<span className="ml-2 text-label font-medium text-apple-mid">회</span></p><p className="mt-2 text-caption text-apple-mid">전체 티켓 입력값 합계 · 미입력 {summary.missingCount}건</p></div>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="card min-w-0"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-section-title font-semibold text-apple-dark">재배포 원인</h2><span className="text-caption text-apple-mid">{scopeLabels[scope]} {scoped.length}건 기준</span></div><p className="mt-2 text-caption text-apple-mid">원인을 선택하면 아래 티켓 목록에 적용됩니다.</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {causes.map((item, index) => <button key={item.name} type="button" aria-pressed={cause === item.name} onClick={() => setCause(cause === item.name ? '' : item.name)} className={`rounded-xl border p-3 text-left hover:bg-apple-gray ${cause === item.name ? 'border-brand-500 bg-brand-50' : 'border-apple-divider'}`}><div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1 text-caption"><span className="font-medium text-apple-dark">{item.name}</span><span className="shrink-0 text-apple-mid">{item.count}건 · {(item.count / scoped.length * 100).toFixed(1)}%</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-apple-gray"><div className="h-full rounded-full" style={{ width: `${item.count / scoped.length * 100}%`, backgroundColor: CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length] }} /></div></button>)}
            {!causes.length && <p className="py-8 text-caption text-apple-mid">해당 범위의 재배포 티켓이 없습니다.</p>}
          </div>
        </section>
        <section className="card min-w-0"><h2 className="text-section-title font-semibold text-apple-dark">월별 재배포 완료</h2><p className="mt-2 text-caption text-apple-mid">완료 티켓의 ‘배포 완료 월’ 입력값 기준 · 단위: 건</p><div className="mt-5 overflow-x-auto"><div className="flex h-56 min-w-max items-end gap-2 border-b border-apple-divider px-1">
          {monthly.months.map((item) => <div key={item.month} className="flex h-full w-8 flex-1 flex-col items-center justify-end" title={`${item.month}: ${item.count}건`}><span className="mb-2 text-caption font-semibold tabular-nums text-apple-dark">{item.count}</span><div className="w-full max-w-10 rounded-t-md bg-brand-500" style={{ height: `${item.count / maximum * 68}%`, minHeight: 2 }} /><span className="my-2 whitespace-nowrap text-control text-apple-mid">{item.month.startsWith('2026-') ? `${Number(item.month.slice(5))}월` : item.month}</span></div>)}
        </div></div><p className="mt-4 text-caption leading-relaxed text-apple-mid">해결일과 배포 완료 월은 다를 수 있습니다. 완료 월 미입력·집계 범위 밖 {monthly.unassigned}건은 그래프에서 제외됩니다.</p>
        </section>
      </div>
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-section-title font-semibold text-apple-dark">재배포 티켓 <span className="ml-1 text-label text-brand-600">{tickets.length}건</span></h2><div className="flex rounded-xl bg-apple-gray p-1">{(['all', 'active', 'closed'] as const).map((value) => <button key={value} aria-pressed={scope === value} onClick={() => changeScope(value)} className={`rounded-lg px-4 py-2 text-control font-medium ${scope === value ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid'}`}>{scopeLabels[value]}</button>)}</div></div>
        <div className="my-4 flex flex-wrap items-center gap-3"><label className="min-w-0 flex-1"><span className="sr-only">재배포 티켓 검색</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="번호, 제목, 고객사, 원인 또는 사유 검색" className="w-full rounded-xl border border-apple-divider bg-apple-surface px-4 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30" /></label>{cause && <button onClick={() => setCause('')} className="rounded-xl bg-brand-50 px-3 py-2 text-control text-brand-700">{cause} · 해제 ×</button>}</div>
        <RedeploymentTickets key={`${scope}:${cause}:${search}`} tickets={tickets} />
        <p className="mt-4 text-caption leading-relaxed text-apple-mid">번호·제목을 누르면 Jira가 새 탭으로 열립니다. 펼치기에서 상세 사유와 담당 정보를 확인할 수 있습니다. 상세 사유 미입력: 전체 {summary.missingReason}건.</p>
      </section>
      <details className="rounded-xl border border-apple-divider bg-apple-surface p-4 text-caption text-apple-mid"><summary className="cursor-pointer font-medium text-apple-dark">집계 기준 및 데이터 안내{report.warnings.length > 0 ? ` · 확인 필요 ${report.warnings.length}건` : ''}</summary><ul className="mt-3 space-y-2 leading-relaxed"><li>Jira의 재배포 여부가 Y인 티켓에서 라이선스 유형을 제외합니다.</li><li>완료: 2026-01-01 이후 해결된 닫힘 티켓. 생성일이 2025년이어도 포함됩니다.</li><li>진행 중: 보고서 생성 시점에 닫히지 않은 재배포 티켓 전체. 완료 통계와 월별 그래프에는 포함되지 않습니다.</li><li>원인·상세 사유·재패치 횟수는 Jira 입력값입니다. 횟수는 실제 배포 일시별 이벤트 수가 아니며 미입력을 0회로 단정하지 않습니다.</li><li>담당자 표기는 업무 배정 정보입니다. 원인으로부터 책임 소재를 추정하지 않습니다.</li><li>모든 데이터는 마지막 갱신 시점 기준입니다. 갱신 실패 시 마지막 저장본을 유지합니다.</li>{report.warnings.map((warning) => <li key={warning} className="text-amber-700">{warning}</li>)}</ul></details>
    </>}
  </div>
}
