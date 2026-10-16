// frontend/src/presentation/components/sla-violations/SlaViolationList.tsx
import { useId, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { ChevronDown, ExternalLink } from 'lucide-react'
import type { SlaViolationTicket } from '@/domain/SlaViolationReport'
import { slaIssueType } from '@/domain/SlaViolationFilters'
import { SLA_VIOLATION_METRICS, slaViolatedMetrics, slaViolationLabel } from '@/domain/SlaViolationMetric'
import { sortSlaViolationTickets } from '@/domain/SlaViolationSort'
import { slaPartnersLabel } from '@/application/services/slaViolationReport'
import { useJira } from '@/presentation/context/JiraContext'
import { slaCreatedDate, slaTimestamp } from '@/presentation/utils/slaViolationFormatters'
import { getIssueTypeLabel } from '@/presentation/utils/issueTypeLabel'
import { useTablePreferences } from '@/presentation/hooks/useTablePreferences'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import SlaStatusDurations from './SlaStatusDurations'
import SlaTicketTargets from './SlaTicketTargets'
import SlaViolationTableHeader, { DEFAULT_SLA_COLUMN_WIDTHS, MIN_SLA_COLUMN_WIDTHS, SLA_TICKET_COLUMNS, resizeSlaColumnWidths } from './SlaViolationTableHeader'

const TICKET_COLUMNS = 'lg:grid-cols-[var(--sla-ticket-columns)]'

function TicketRow({ ticket }: { ticket: SlaViolationTicket }) {
  const [expanded, setExpanded] = useState(false)
  const detailsId = useId()
  const { jiraBrowse } = useJira()
  const facts: [string, ReactNode][] = [
    ['고객사명', ticket.customer], ['담당 파트너사', slaPartnersLabel(ticket.partners)],
    ['보고자', ticket.reporter], ['담당자', ticket.assignee], ['TAC 담당자', ticket.tac_assignee],
    ['현재 체류 상태', <StatusBadge status={ticket.current_status || '확인 불가'} size="md" />],
  ]
  return (
    <li className="border-t border-apple-divider/70">
      <div className="flex items-stretch gap-1 px-3 sm:px-5">
        <a href={`${jiraBrowse}/${encodeURIComponent(ticket.key)}`} target="_blank" rel="noopener noreferrer"
          className={`grid min-w-0 flex-1 grid-cols-2 items-center gap-x-4 gap-y-2 rounded-xl px-1 py-4 text-body transition-colors hover:bg-apple-gray focus-visible:outline-brand-400 ${TICKET_COLUMNS}`}
          aria-label={`${ticket.key} ${ticket.summary} · ${slaViolationLabel(ticket)} · Jira 새 탭에서 열기`}>
          <span className="col-span-2 row-start-1 flex min-w-0 items-center gap-1.5 font-semibold text-brand-600 lg:col-span-1 lg:row-auto"><span className="min-w-0 break-all">{ticket.key}</span><ExternalLink size={12} className="shrink-0" aria-hidden="true" /></span>
          <span className="col-span-2 row-start-2 break-words font-medium text-apple-dark lg:col-span-1 lg:row-auto">{ticket.summary}</span>
          <span className="col-span-2 row-start-3 min-w-0 break-words text-label text-apple-mid lg:col-span-1 lg:row-auto"><span className="mr-1.5 lg:hidden">유형</span><IssueTypeBadge type={getIssueTypeLabel(slaIssueType(ticket))} className="max-w-full whitespace-normal break-words" /></span>
          <span className="col-span-2 row-start-4 min-w-0 lg:col-span-1 lg:row-auto">
            <span className="mb-1 block text-label text-apple-mid lg:hidden">위반 항목</span>
            <span className="flex flex-wrap gap-1.5">{slaViolatedMetrics(ticket).map(({ key, label }) => <span key={key} className={`max-w-full rounded-full px-2.5 py-1 text-caption font-medium ${key === 'initial_response' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>{label}</span>)}</span>
          </span>
          <span className="row-start-5 text-label tabular-nums text-apple-mid lg:row-auto"><span className="mb-0.5 block lg:hidden">생성일</span>{slaCreatedDate(ticket.created_at)}</span>
          <span className="row-start-5 text-right text-label tabular-nums text-apple-mid lg:row-auto"><span className="mb-0.5 block lg:hidden">경과일</span>{ticket.elapsed_days.toLocaleString('ko-KR')}일</span>
        </a>
        <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} aria-controls={detailsId}
          aria-label={`${ticket.key} 상세 ${expanded ? '접기' : '펼치기'}`}
          className="my-2 flex w-12 shrink-0 flex-col items-center justify-center gap-1 rounded-xl text-apple-mid transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-brand-400">
          <ChevronDown size={17} aria-hidden="true" className={`transition-transform ${expanded ? 'rotate-180' : ''}`} /><span className="text-control-label">{expanded ? '접기' : '펼치기'}</span>
        </button>
      </div>
      {expanded && (
        <div id={detailsId} className="mx-4 mb-4 rounded-xl bg-apple-gray/70 p-4 sm:mx-6 sm:p-5">
          <SlaTicketTargets ticket={ticket} />
          {ticket.sla_cycles == null && <div className="mb-5">
            <h3 className="text-section-label font-semibold text-apple-mid">SLA 위반 당시의 티켓 상태</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {ticket.breaches.map((breach, index) => (
                <li key={`${breach.metric}-${breach.breached_at}-${index}`} className="rounded-lg border border-apple-divider bg-apple-surface px-3 py-2">
                  <span className="mb-1 block text-caption font-medium text-apple-mid">{SLA_VIOLATION_METRICS.find(({ key }) => key === breach.metric)?.label}</span>
                  <StatusBadge status={breach.status || '확인 불가'} size="md" />
                  <span className="ml-2 text-label text-apple-mid">{slaTimestamp(breach.breached_at)}{breach.breached_at ? ' KST' : ''}</span>
                </li>
              ))}
            </ul>
          </div>}
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
            {facts.map(([label, value]) => (
              <div key={label} className="min-w-0"><dt className="text-caption text-apple-mid">{label}</dt><dd className="mt-1 break-words text-metric font-medium text-apple-dark">{value || '확인 불가'}</dd></div>
            ))}
          </dl>
          <div className="mt-5 border-t border-apple-divider pt-4">
            <SlaStatusDurations durations={ticket.status_durations} />
          </div>
          {ticket.warnings.length > 0 && <div className="mt-4 text-caption text-amber-700"><p className="font-medium">일부 상세 정보 확인 필요</p><ul className="mt-1 space-y-1">{ticket.warnings.map((warning, index) => <li key={index} className="break-words">{warning}</li>)}</ul></div>}
        </div>
      )}
    </li>
  )
}

export default function SlaViolationList({ tickets, isFiltered = false }: { tickets: SlaViolationTicket[]; isFiltered?: boolean }) {
  const { sort, setSort, widths, setWidths } = useTablePreferences('sla-violations:combined', DEFAULT_SLA_COLUMN_WIDTHS, MIN_SLA_COLUMN_WIDTHS)
  const sortedTickets = useMemo(() => sortSlaViolationTickets(tickets, sort), [tickets, sort])
  const titleId = useId()
  const gridStyle = { '--sla-ticket-columns': SLA_TICKET_COLUMNS.map(({ key }) => `minmax(0, ${widths[key]}fr)`).join(' ') } as CSSProperties
  return (
    <section aria-labelledby={titleId} style={gridStyle} className="min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm">
      <div className="flex items-center gap-2 px-5 py-5">
        <h2 id={titleId} className="text-section-title font-semibold text-apple-dark">SLA 위반 티켓</h2>
        <span className="rounded-full bg-brand-50 px-3 py-1 text-label font-semibold tabular-nums text-brand-700">{sortedTickets.length.toLocaleString('ko-KR')}건</span>
      </div>
      {sortedTickets.length > 0 ? (
        <>
          <SlaViolationTableHeader label="SLA 위반 티켓" sort={sort} widths={widths} onSort={setSort}
            onResize={(left, right, delta) => setWidths((current) => resizeSlaColumnWidths(current, left, right, delta))} />
          <ul>{sortedTickets.map((ticket) => <TicketRow key={ticket.key} ticket={ticket} />)}</ul>
        </>
      ) : <p className="border-t border-apple-divider/70 px-5 py-12 text-center text-label text-apple-mid">{isFiltered ? '선택한 필터에 맞는' : '해당 기간에 생성된'} SLA 위반 티켓이 없습니다.</p>}
    </section>
  )
}
