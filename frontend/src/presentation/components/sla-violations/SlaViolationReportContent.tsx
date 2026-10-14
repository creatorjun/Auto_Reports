// frontend/src/presentation/components/sla-violations/SlaViolationReportContent.tsx
import { useMemo, useState } from 'react'
import type { Semester } from '@/domain/Dashboard'
import type { SlaViolationReport } from '@/domain/SlaViolationReport'
import { filterSlaViolationTickets, slaViolationFilterOptions } from '@/domain/SlaViolationFilters'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import SlaViolationList from '@/presentation/components/sla-violations/SlaViolationList'

export default function SlaViolationReportContent({ report }: { report: SlaViolationReport }) {
  const [selectedTypes, setSelectedTypes] = useState<Set<string> | null>(null)
  const [selectedStatuses, setSelectedStatuses] = useState<Set<string> | null>(null)
  const [selectedSemester, setSelectedSemester] = useState<Semester | null>(null)
  const options = useMemo(() => slaViolationFilterOptions(report.tickets), [report.tickets])
  const tickets = useMemo(() => filterSlaViolationTickets(report.tickets, selectedTypes, selectedStatuses, selectedSemester), [report.tickets, selectedTypes, selectedStatuses, selectedSemester])
  const isFiltered = selectedTypes !== null || selectedStatuses !== null || selectedSemester !== null
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
        onToggle={(value) => setSelectedTypes((current) => toggle(current, options.issueTypes, value))}
        onStatusToggle={(value) => setSelectedStatuses((current) => toggle(current, options.statuses, value))}
        onSemesterChange={setSelectedSemester}
        onToggleAll={(selected) => { setSelectedTypes(selected ? null : new Set()); setSelectedStatuses(selected ? null : new Set()) }} />
      <p className="text-caption leading-relaxed text-apple-mid">요청 유형·현재 상태는 보고서 생성 시점 기준이며, 상·하반기는 저장된 티켓의 생성일(KST) 기준입니다. 필터는 두 목록에 즉시 적용됩니다.</p>
      {options.unknownTypeCount > 0 && <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-caption text-amber-800">요청 유형이 저장되지 않은 티켓 {options.unknownTypeCount.toLocaleString('ko-KR')}건은 ‘확인 불가’로 표시합니다. 보고서를 다시 생성하면 요청 유형을 수집합니다.</p>}
      {report.warnings.length > 0 && <details className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-label text-amber-800"><summary className="cursor-pointer font-medium">일부 데이터 확인 필요 ({report.warnings.length})</summary><ul className="mt-2 space-y-1 text-caption">{report.warnings.map((warning, index) => <li key={index} className="break-words">{warning}</li>)}</ul></details>}
      <SlaViolationList tickets={tickets} metric="initial_response" isFiltered={isFiltered} />
      <SlaViolationList tickets={tickets} metric="resolution" isFiltered={isFiltered} />
    </>
  )
}
