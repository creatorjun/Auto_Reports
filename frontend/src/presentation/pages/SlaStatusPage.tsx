// frontend/src/presentation/pages/SlaStatusPage.tsx
import { useEffect, useMemo, useState } from 'react'
import { Loader2, RefreshCw, Search, X } from 'lucide-react'
import type { SlaStatusFilters } from '@/domain/SLAStatus'
import { RequestError } from '@/application/errors/RequestError'
import { defaultSlaStatusFilters, filterSlaStatusTickets, slaStatusFilterOptions } from '@/application/services/slaStatus'
import { useSlaStatus } from '@/presentation/hooks/useSlaStatus'
import { useReportStore } from '@/presentation/state/reportStore'
import { slaTimestamp } from '@/presentation/utils/slaViolationFormatters'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SlaStatusOverview from '@/presentation/components/sla-status/SlaStatusOverview'
import SlaStatusList from '@/presentation/components/sla-status/SlaStatusList'

export default function SlaStatusPage() {
  const query = useSlaStatus()
  const snapshot = query.data
  const [filters, setFilters] = useState(defaultSlaStatusFilters)
  const [selectedStageName, setSelectedStageName] = useState('')
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  const options = useMemo(() => slaStatusFilterOptions(snapshot?.tickets ?? []), [snapshot])
  const tickets = useMemo(() => filterSlaStatusTickets(snapshot?.tickets ?? [], filters), [snapshot, filters])
  const update = <K extends keyof SlaStatusFilters>(key: K, value: SlaStatusFilters[K]) => setFilters((previous) => ({ ...previous, [key]: value }))
  const isFiltered = filters.scope !== 'all' || !!filters.search.trim() || !!filters.status || !!filters.stage
  const selectStage = (stage: string) => {
    setSelectedStageName(options.stages.find((option) => option.id === stage)?.name ?? '')
    update('stage', stage)
  }
  const collectionStatus = snapshot ? `수집 시각 ${slaTimestamp(snapshot.generated_at)} (KST)` : query.refreshing ? '최초 데이터를 불러오고 있습니다.' : '아직 수집된 데이터가 없습니다.'
  const error = query.refreshError ?? query.error
  const errorText = typeof error === 'string' ? error : error instanceof RequestError && typeof error.detail === 'string' ? error.detail : 'SLA 현황을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-content flex-col gap-5 3xl:max-w-none">
      <header className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-page-title font-semibold tracking-tight text-apple-dark">SLA 현황</h1><p className="mt-2 text-label text-apple-mid">현재 진행 또는 일시정지 중인 SLA 중 잔여 비율이 {snapshot?.threshold_percent ?? 30}% 미만인 티켓입니다. 이미 SLA를 위반한 티켓은 제외합니다.</p><p className="mt-2 text-caption text-apple-mid">{collectionStatus} · 수집 시점 기준</p></div><button type="button" onClick={query.refresh} disabled={query.refreshing} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-control font-medium text-white hover:bg-brand-700 disabled:cursor-wait disabled:opacity-50">{query.refreshing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}{query.refreshing ? '수집 중' : '새로고침'}</button></header>
      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-label text-red-700">{errorText}{snapshot && <p className="mt-1">마지막으로 수집한 데이터를 유지하고 있습니다. 수집 시각을 확인하고 다시 새로고침해 주세요.</p>}</div>}
      {query.refreshing && snapshot && <p role="status" className="text-caption text-apple-mid">최신 SLA와 상태 이력을 수집하고 있습니다. 완료될 때까지 기존 데이터를 표시합니다.</p>}
      {!snapshot && query.refreshing && <LoadingSpinner text="SLA와 상태 이력을 수집하고 있습니다. 티켓 수에 따라 잠시 걸릴 수 있습니다." />}
      {snapshot && <>
        <SlaStatusOverview tickets={snapshot.tickets} scope={filters.scope} onChange={(scope) => update('scope', scope)} />
        <p className="-mt-2 text-caption text-apple-mid">전체 {snapshot.ticket_count.toLocaleString('ko-KR')}개 티켓 · 대상 SLA {snapshot.sla_count.toLocaleString('ko-KR')}개. 위젯은 전체 수집 결과 기준이며, 한 티켓에 진행 중·일시정지 SLA가 함께 있으면 각 위젯에 포함됩니다.</p>
        <section aria-label="SLA 현황 필터" className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm sm:p-5"><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr]"><label className="min-w-0 text-control-label font-medium text-apple-mid">검색<span className="relative mt-2 block"><Search size={16} className="pointer-events-none absolute left-3 top-3 text-apple-light" aria-hidden="true" /><input type="search" value={filters.search} onChange={(event) => update('search', event.target.value)} placeholder="티켓 번호, 제목, 담당자 검색" className="w-full rounded-xl border border-apple-divider bg-apple-surface py-2.5 pl-9 pr-3 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30" /></span></label><label className="min-w-0 text-control-label font-medium text-apple-mid">현재 상태<select value={filters.status} onChange={(event) => update('status', event.target.value)} className="mt-2 block w-full rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark"><option value="">전체 상태</option>{filters.status && !options.statuses.includes(filters.status) && <option value={filters.status}>{filters.status} (현재 결과 없음)</option>}{options.statuses.map((status) => <option key={status} value={status}>{status || '확인 불가'}</option>)}</select></label><label className="min-w-0 text-control-label font-medium text-apple-mid">SLA 단계<select value={filters.stage} onChange={(event) => selectStage(event.target.value)} className="mt-2 block w-full rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark"><option value="">전체 SLA</option>{filters.stage && !options.stages.some((stage) => stage.id === filters.stage) && <option value={filters.stage}>{selectedStageName || filters.stage} (현재 결과 없음)</option>}{options.stages.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}</select></label></div><div className="mt-3 flex flex-wrap items-center justify-between gap-3"><p className="text-caption text-apple-mid">선택한 위젯과 상태·SLA 단계·검색 조건을 함께 적용합니다.</p><button type="button" onClick={() => setFilters(defaultSlaStatusFilters())} disabled={!isFiltered && filters.sort === 'remaining_percent'} className="inline-flex items-center gap-1.5 rounded-lg border border-apple-divider px-3 py-2 text-control text-apple-mid hover:bg-apple-gray disabled:opacity-40"><X size={14} aria-hidden="true" />필터 초기화</button></div></section>
        <div className="flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-label text-apple-mid">검색 결과 <strong className="font-semibold text-apple-dark">{tickets.length.toLocaleString('ko-KR')}건</strong><span className="ml-2 text-caption">대상 SLA {tickets.reduce((sum, ticket) => sum + ticket.slas.length, 0).toLocaleString('ko-KR')}개</span></p><label className="inline-flex items-center gap-2 text-caption text-apple-mid">정렬<select value={filters.sort} onChange={(event) => update('sort', event.target.value as SlaStatusFilters['sort'])} className="rounded-xl border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark"><option value="remaining_percent">잔여 비율 낮은순</option><option value="remaining_millis">잔여 시간 짧은순</option><option value="key">티켓 번호순</option></select></label></div>
        <SlaStatusList tickets={tickets} isFiltered={isFiltered} />
      </>}
    </div>
  )
}
