// frontend/src/presentation/pages/RedeploymentPage.tsx
import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Loader2, RotateCcw } from 'lucide-react'
import type { RedeploymentColumn, RedeploymentColumnFilters, RedeploymentScope } from '@/domain/RedeploymentReport'
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
  const [columnFilters, setColumnFilters] = useState<RedeploymentColumnFilters>({})
  const [month, setMonth] = useState('')
  const selectedScope = month ? 'closed' : scope
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  const summary = useMemo(() => redeploymentSummary(report?.tickets ?? []), [report])
  const scoped = useMemo(() => filterRedeployments(report?.tickets ?? [], selectedScope, '', ''), [report, selectedScope])
  const causes = useMemo(() => redeploymentSummary(scoped).causes, [scoped])
  const tickets = useMemo(() => filterRedeployments(scoped, 'all', cause, search, month, columnFilters), [scoped, cause, search, month, columnFilters])
  const monthly = useMemo(() => report ? redeploymentMonths(report) : { months: [], unassigned: 0 }, [report])
  const maximum = Math.max(1, ...monthly.months.map((item) => item.count))
  const error = refresh.error ?? query.error
  const changeScope = (value: RedeploymentScope) => { setScope(value); setCause(''); setMonth('') }
  const changeColumnFilter = (column: RedeploymentColumn, value: string) => setColumnFilters((current) => ({ ...current, [column]: value }))
  const hasDetailFilters = Boolean(search || month || cause || Object.values(columnFilters).some(Boolean))
  const resetDetailFilters = () => { setSearch(''); setColumnFilters({}); setMonth(''); setCause('') }

  return <div className="mx-auto flex w-full max-w-content flex-col gap-5 break-keep 3xl:max-w-none">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><h1 className="text-page-title font-semibold tracking-tight text-apple-dark">재배포 현황</h1></div>
      <button type="button" disabled={refresh.isPending} onClick={() => refresh.mutate()} className="flex min-h-11 items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-medium text-white hover:bg-brand-700 disabled:opacity-50">{refresh.isPending ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}{refresh.isPending ? '갱신 중' : '지금 갱신'}</button>
    </header>
    {refresh.isPending && <p role="status" className="text-label text-apple-mid">Jira에서 최신 재배포 정보를 수집하고 저장하고 있습니다.</p>}
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-label text-red-700">{error instanceof RequestError && typeof error.detail === 'string' ? error.detail : '보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'}<button onClick={() => void query.refetch()} className="ml-3 underline">다시 불러오기</button></div>}
    {report && redeploymentIsStale(report.generated_at) && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-caption text-amber-800">오늘 정기 갱신 시각 이후의 보고서가 아직 없습니다. 마지막으로 저장된 데이터를 표시합니다. 잠시 후 확인하거나 ‘지금 갱신’을 눌러 주세요.</p>}
    {query.isLoading && <LoadingSpinner text="마지막 재배포 보고서를 불러오는 중..." />}
    {!query.isLoading && !report && !query.isError && <div className="card py-14 text-center"><RotateCcw size={32} className="mx-auto mb-3 text-brand-600" /><h2 className="text-section-title font-semibold text-apple-dark">첫 재배포 보고서를 준비하고 있습니다.</h2><p className="mt-2 text-label text-apple-mid">자동 생성이 끝나면 표시됩니다. ‘지금 갱신’으로 직접 생성할 수도 있습니다.</p></div>}
    {report && <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {([
          ['all', '재배포 티켓', summary.total],
          ['closed', '완료', summary.closed],
          ['active', '진행 중', summary.active],
        ] as const).map(([value, label, count]) => <button key={value} onClick={() => changeScope(value)} aria-pressed={selectedScope === value} className={`card text-left transition-shadow hover:shadow-md ${selectedScope === value ? 'ring-2 ring-brand-400' : ''}`}><p className="flex items-center gap-2 text-label font-semibold text-apple-dark">{value === 'closed' ? <CheckCircle2 size={18} className="text-green-600" /> : <RotateCcw size={18} className="text-brand-600" />}{label}</p><p className="mt-3 text-metric-compact font-semibold tabular-nums text-apple-dark">{count}<span className="ml-2 text-label font-medium text-apple-mid">건</span></p></button>)}
        <div className="card"><p className="text-label font-semibold text-apple-dark">기록된 재패치 횟수</p><p className="mt-3 text-metric-compact font-semibold tabular-nums text-apple-dark">{summary.repatches}<span className="ml-2 text-label font-medium text-apple-mid">회</span></p>{summary.missingCount > 0 && <p className="mt-2 text-caption text-apple-mid">횟수 미입력 {summary.missingCount}건</p>}</div>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="card min-w-0"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-section-title font-semibold text-apple-dark">재배포 원인</h2><span className="text-caption text-apple-mid">{scopeLabels[selectedScope]} {scoped.length}건 기준</span></div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {causes.map((item, index) => <button key={item.name} type="button" aria-pressed={cause === item.name} onClick={() => setCause(cause === item.name ? '' : item.name)} className={`rounded-xl border p-3 text-left hover:bg-apple-gray ${cause === item.name ? 'border-brand-500 bg-brand-50' : 'border-apple-divider'}`}><div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1 text-caption"><span className="font-medium text-apple-dark">{item.name}</span><span className="shrink-0 text-apple-mid">{item.count}건 · {(item.count / scoped.length * 100).toFixed(1)}%</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-apple-gray"><div className="h-full rounded-full" style={{ width: `${item.count / scoped.length * 100}%`, backgroundColor: CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length] }} /></div></button>)}
            {!causes.length && <p className="py-8 text-caption text-apple-mid">해당 범위의 재배포 티켓이 없습니다.</p>}
          </div>
        </section>
        <section className="card min-w-0"><h2 className="text-section-title font-semibold text-apple-dark">월별 재배포 완료</h2><div className="mt-5 overflow-x-auto"><div className="flex h-56 min-w-max items-end gap-2 border-b border-apple-divider px-1">
          {monthly.months.map((item) => <button key={item.month} type="button" aria-label={`${item.month} 재배포 완료 ${item.count}건`} aria-pressed={month === item.month} onClick={() => setMonth(month === item.month ? '' : item.month)} className={`flex h-full w-8 flex-1 flex-col items-center justify-end rounded-t-lg transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${month === item.month ? 'bg-brand-50 ring-2 ring-brand-400' : ''}`} title={`${item.month}: ${item.count}건`}><span className="mb-2 text-caption font-semibold tabular-nums text-apple-dark">{item.count}</span><span className={`w-full max-w-10 rounded-t-md ${month === item.month ? 'bg-brand-700' : 'bg-brand-500'}`} style={{ height: `${item.count / maximum * 68}%`, minHeight: 2 }} /><span className={`my-2 whitespace-nowrap text-control ${month === item.month ? 'font-semibold text-brand-700' : 'text-apple-mid'}`}>{item.month.startsWith('2026-') ? `${Number(item.month.slice(5))}월` : item.month}</span></button>)}
        </div></div>{monthly.unassigned > 0 && <p role="status" className="mt-4 text-caption text-apple-mid">완료 월 미입력·범위 밖 {monthly.unassigned}건</p>}
        </section>
      </div>
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-section-title font-semibold text-apple-dark">재배포 티켓 <span className="ml-1 text-label text-brand-600">{tickets.length}건</span></h2><div className="flex rounded-xl bg-apple-gray p-1">{(['all', 'active', 'closed'] as const).map((value) => <button key={value} aria-pressed={selectedScope === value} onClick={() => changeScope(value)} className={`rounded-lg px-4 py-2 text-control font-medium ${selectedScope === value ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid'}`}>{scopeLabels[value]}</button>)}</div></div>
        <div className="my-4 flex flex-wrap items-center gap-3"><label className="min-w-0 flex-1"><span className="sr-only">재배포 티켓 검색</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="번호, 제목, 고객사, 원인 또는 사유 검색" className="w-full rounded-xl border border-apple-divider bg-apple-surface px-4 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30" /></label>{month && <button onClick={() => setMonth('')} className="rounded-xl bg-brand-50 px-3 py-2 text-control text-brand-700">{month} · 해제 ×</button>}{cause && <button onClick={() => setCause('')} className="rounded-xl bg-brand-50 px-3 py-2 text-control text-brand-700">{cause} · 해제 ×</button>}<button type="button" disabled={!hasDetailFilters} onClick={resetDetailFilters} className="min-h-11 rounded-xl px-3 py-2 text-control font-medium text-apple-mid hover:bg-apple-gray focus-visible:outline-brand-400 disabled:opacity-40">초기화</button></div>
        <RedeploymentTickets tickets={tickets} columnFilters={columnFilters} onColumnFilterChange={changeColumnFilter} paginationResetKey={JSON.stringify([selectedScope, month, cause, search, columnFilters])} />
        {summary.missingReason > 0 && <p className="mt-4 text-caption text-apple-mid">상세 사유 미입력 {summary.missingReason}건</p>}
      </section>
      {report.warnings.length > 0 && <details className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-caption text-amber-800"><summary className="cursor-pointer font-medium">일부 데이터 확인 필요 ({report.warnings.length})</summary><ul className="mt-3 space-y-2 leading-relaxed">{report.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}
    </>}
  </div>
}
