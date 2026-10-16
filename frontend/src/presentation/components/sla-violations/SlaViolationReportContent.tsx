// frontend/src/presentation/components/sla-violations/SlaViolationReportContent.tsx
import { useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import type { Semester } from '@/domain/Dashboard'
import type { SlaViolationReport } from '@/domain/SlaViolationReport'
import { defaultSlaSelectedStatuses, filterSlaViolationTickets, slaViolationFilterOptions } from '@/domain/SlaViolationFilters'
import { filterSlaViolationDetails, filterSlaViolationScope, type SlaViolationScope } from '@/domain/SlaViolationOverview'
import { SLA_OVERVIEW_SCOPES } from '@/presentation/config/slaViolationOverview'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import SlaViolationList from '@/presentation/components/sla-violations/SlaViolationList'
import SlaViolationOverview from './SlaViolationOverview'

export default function SlaViolationReportContent({ report }: { report: SlaViolationReport }) {
  const [selectedTypes, setSelectedTypes] = useState<Set<string> | null>(null)
  const [selectedStatuses, setSelectedStatuses] = useState<Set<string> | null>(() => defaultSlaSelectedStatuses(report.tickets))
  const [selectedSemester, setSelectedSemester] = useState<Semester | null>(null)
  const [scope, setScope] = useState<SlaViolationScope>('all')
  const [status, setStatus] = useState<string | null>(null)
  const [bucket, setBucket] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const options = useMemo(() => slaViolationFilterOptions(report.tickets), [report.tickets])
  const tickets = useMemo(() => filterSlaViolationTickets(report.tickets, selectedTypes, selectedStatuses, selectedSemester), [report.tickets, selectedTypes, selectedStatuses, selectedSemester])
  const scopedTickets = useMemo(() => filterSlaViolationScope(tickets, scope), [tickets, scope])
  const visibleTickets = useMemo(() => filterSlaViolationDetails(scopedTickets, report.period, status, bucket, search), [scopedTickets, report.period, status, bucket, search])
  const hasDetailFilter = scope !== 'all' || status !== null || bucket !== null || search.trim() !== ''
  const isFiltered = selectedTypes !== null || selectedStatuses !== null || selectedSemester !== null || hasDetailFilter
  const clearChartSelection = () => { setStatus(null); setBucket(null) }
  const changeScope = (value: SlaViolationScope) => { setScope(value); clearChartSelection() }
  const resetDetails = () => { changeScope('all'); setSearch('') }
  const toggle = (current: Set<string> | null, all: string[], value: string) => {
    const next = new Set(current ?? all)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next.size === all.length && all.every((item) => next.has(item)) ? null : next
  }

  return (
    <>
      <IssueTypeFilter issueTypes={options.issueTypes} statuses={options.statuses}
        selectedTypes={selectedTypes} selectedStatuses={selectedStatuses} selectedSemester={selectedSemester}
        supported statusSupported semesterSupported
        onToggle={(value) => { setSelectedTypes((current) => toggle(current, options.issueTypes, value)); clearChartSelection() }}
        onStatusToggle={(value) => { setSelectedStatuses((current) => toggle(current, options.statuses, value)); clearChartSelection() }}
        onSemesterChange={(value) => { setSelectedSemester(value); clearChartSelection() }}
        onToggleAll={(selected) => { setSelectedTypes(selected ? null : new Set()); setSelectedStatuses(selected ? null : new Set()); clearChartSelection() }} />
      <SlaViolationOverview report={report} tickets={tickets} scopedTickets={scopedTickets} scope={scope} status={status} bucket={bucket}
        onScopeChange={changeScope} onStatusChange={setStatus} onBucketChange={setBucket} />
      {options.unknownTypeCount > 0 && <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-caption text-amber-800">요청 유형이 저장되지 않은 티켓 {options.unknownTypeCount.toLocaleString('ko-KR')}건은 ‘확인 불가’로 표시합니다. 보고서를 다시 생성하면 요청 유형을 수집합니다.</p>}
      {report.warnings.length > 0 && <details className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-label text-amber-800"><summary className="cursor-pointer font-medium">일부 데이터 확인 필요 ({report.warnings.length})</summary><ul className="mt-2 space-y-1 text-caption">{report.warnings.map((warning, index) => <li key={index} className="break-words">{warning}</li>)}</ul></details>}
      <section aria-label="위반 티켓 검색" className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-section-title font-semibold text-apple-dark">위반 티켓<span className="text-label tabular-nums text-brand-600">{visibleTickets.length.toLocaleString('ko-KR')}건</span></h2>
          <label className="relative w-full sm:w-80">
            <span className="sr-only">SLA 티켓 검색</span><Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 text-apple-light" />
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="번호, 제목, 고객사, 담당자 검색" className="w-full rounded-xl border border-apple-divider bg-apple-surface py-2.5 pl-9 pr-3 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30" />
          </label>
        </div>
        {hasDetailFilter && <div className="flex flex-wrap items-center gap-2">
          {[
            ...(scope !== 'all' ? [{ label: SLA_OVERVIEW_SCOPES.find((item) => item.key === scope)!.label, clear: () => changeScope('all') }] : []),
            ...(status !== null ? [{ label: status, clear: () => setStatus(null) }] : []),
            ...(bucket !== null ? [{ label: report.period === 'year' ? `${Number(bucket.slice(5))}월` : bucket, clear: () => setBucket(null) }] : []),
          ].map(({ label, clear }) => <button key={label} type="button" onClick={clear} aria-label={`${label} 선택 해제`} className="flex items-center gap-1.5 rounded-lg bg-brand-50 px-3 py-2 text-control text-brand-700">{label}<X size={14} aria-hidden="true" /></button>)}
          <button type="button" onClick={resetDetails} className="ml-auto rounded-lg px-3 py-2 text-control font-medium text-apple-mid hover:bg-apple-gray">상세 필터 초기화</button>
        </div>}
      </section>
      <SlaViolationList tickets={visibleTickets} isFiltered={isFiltered} />
    </>
  )
}
