// frontend/src/presentation/components/sla-violations/SlaViolationList.tsx
import { useId, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ChevronDown, ExternalLink } from 'lucide-react'
import type { SlaViolationMetric, SlaViolationTicket } from '@/domain/SlaViolationReport'
import { slaIssueType } from '@/domain/SlaViolationFilters'
import { sortSlaViolationTickets } from '@/domain/SlaViolationSort'
import type { SlaViolationSort } from '@/domain/SlaViolationSort'
import { SLA_METRIC_LABELS, slaPartnersLabel, slaTicketsForMetric } from '@/application/services/slaViolationReport'
import { useJira } from '@/presentation/context/JiraContext'
import { slaCreatedDate, slaTimestamp } from '@/presentation/utils/slaViolationFormatters'
import { getIssueTypeLabel } from '@/presentation/utils/issueTypeLabel'
import SlaViolationTableHeader, { DEFAULT_SLA_COLUMN_WIDTHS, SLA_TICKET_COLUMNS, resizeSlaColumnWidths } from './SlaViolationTableHeader'

const TICKET_COLUMNS = 'lg:grid-cols-[var(--sla-ticket-columns)]'

function TicketRow({ ticket, metric }: { ticket: SlaViolationTicket; metric: SlaViolationMetric }) {
  const [expanded, setExpanded] = useState(false)
  const detailsId = useId()
  const { jiraBrowse } = useJira()
  const facts = [
    ['고객사명', ticket.customer], ['담당 파트너사', slaPartnersLabel(ticket.partners)],
    ['보고자', ticket.reporter], ['담당자', ticket.assignee], ['TAC 담당자', ticket.tac_assignee],
    ['현재 체류 상태', ticket.current_status],
  ]
  return (
    <li className="border-t border-apple-divider/70">
      <div className="flex items-stretch gap-1 px-3 sm:px-5">
        <a href={`${jiraBrowse}/${encodeURIComponent(ticket.key)}`} target="_blank" rel="noopener noreferrer"
          className={`grid min-w-0 flex-1 grid-cols-2 items-center gap-x-4 gap-y-2 rounded-xl px-1 py-4 text-sm transition-colors hover:bg-apple-gray focus-visible:outline-brand-400 ${TICKET_COLUMNS}`}
          aria-label={`${ticket.key} ${ticket.summary} · Jira 새 탭에서 열기`}>
          <span className="col-span-2 row-start-1 flex min-w-0 items-center gap-1.5 font-semibold text-brand-600 lg:col-span-1 lg:row-auto"><span className="min-w-0 break-all">{ticket.key}</span><ExternalLink size={12} className="shrink-0" aria-hidden="true" /></span>
          <span className="col-span-2 row-start-2 break-words font-medium text-apple-dark lg:col-span-1 lg:row-auto">{ticket.summary}</span>
          <span className="col-span-2 row-start-3 min-w-0 break-words text-xs text-apple-mid lg:col-span-1 lg:row-auto"><span className="mr-1.5 lg:hidden">유형</span>{getIssueTypeLabel(slaIssueType(ticket))}</span>
          <span className="row-start-4 text-xs tabular-nums text-apple-mid lg:row-auto"><span className="mr-1.5 lg:hidden">생성일</span>{slaCreatedDate(ticket.created_at)}</span>
          <span className="row-start-4 text-right text-xs tabular-nums text-apple-mid lg:row-auto"><span className="mr-1.5 lg:hidden">경과일</span>{ticket.elapsed_days.toLocaleString('ko-KR')}일</span>
        </a>
        <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} aria-controls={detailsId}
          aria-label={`${ticket.key} 상세 ${expanded ? '접기' : '펼치기'}`}
          className="my-2 flex w-12 shrink-0 flex-col items-center justify-center gap-1 rounded-xl text-apple-mid transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-brand-400">
          <ChevronDown size={17} aria-hidden="true" className={`transition-transform ${expanded ? 'rotate-180' : ''}`} /><span className="text-[10px]">{expanded ? '접기' : '펼치기'}</span>
        </button>
      </div>
      {expanded && (
        <div id={detailsId} className="mx-4 mb-4 rounded-xl bg-apple-gray/70 p-4 sm:mx-6 sm:p-5">
          <div className="mb-5">
            <h3 className="text-xs font-semibold text-apple-mid">SLA 위반 당시의 티켓 상태</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {ticket.breaches.filter((breach) => breach.metric === metric).map((breach, index) => (
                <li key={`${breach.breached_at}-${index}`} className="rounded-lg border border-apple-divider bg-apple-surface px-3 py-2">
                  <span className="text-sm font-semibold text-apple-dark">{breach.status || '확인 불가'}</span>
                  <span className="ml-2 text-xs text-apple-mid">{slaTimestamp(breach.breached_at)}{breach.breached_at ? ' KST' : ''}</span>
                </li>
              ))}
            </ul>
          </div>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
            {facts.map(([label, value]) => (
              <div key={label}><dt className="text-xs text-apple-mid">{label}</dt><dd className="mt-1 break-words text-sm font-medium text-apple-dark">{value || '확인 불가'}</dd></div>
            ))}
          </dl>
          <div className="mt-5 border-t border-apple-divider pt-4">
            <h3 className="text-xs font-semibold text-apple-mid">각 상태별 체류 기간 <span className="font-normal">· 보고서 생성 시점까지의 실제 경과시간</span></h3>
            {ticket.status_durations ? (
              <dl className="mt-3 flex flex-wrap gap-2">
                {ticket.status_durations.map(({ status, hours }) => (
                  <div key={status} className="flex items-center gap-2 rounded-lg bg-apple-surface px-3 py-2 text-xs"><dt className="text-apple-mid">{status}</dt><dd className="font-semibold tabular-nums text-apple-dark">{hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}시간</dd></div>
                ))}
              </dl>
            ) : <p className="mt-2 text-xs text-apple-mid">상태 변경 이력이 불완전하여 체류 기간을 확인할 수 없습니다.</p>}
          </div>
          {ticket.warnings.length > 0 && <div className="mt-4 text-xs text-amber-700"><p className="font-medium">일부 상세 정보 확인 필요</p><ul className="mt-1 space-y-1">{ticket.warnings.map((warning, index) => <li key={index} className="break-words">{warning}</li>)}</ul></div>}
        </div>
      )}
    </li>
  )
}

export default function SlaViolationList({ tickets, metric, isFiltered = false }: { tickets: SlaViolationTicket[]; metric: SlaViolationMetric; isFiltered?: boolean }) {
  const [sort, setSort] = useState<SlaViolationSort | null>(null)
  const [widths, setWidths] = useState(DEFAULT_SLA_COLUMN_WIDTHS)
  const filtered = useMemo(() => sortSlaViolationTickets(slaTicketsForMetric(tickets, metric), sort), [tickets, metric, sort])
  const titleId = useId()
  const gridStyle = { '--sla-ticket-columns': SLA_TICKET_COLUMNS.map(({ key }) => `minmax(0, ${widths[key]}fr)`).join(' ') } as CSSProperties
  return (
    <section aria-labelledby={titleId} style={gridStyle} className="min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm">
      <div className="flex items-center justify-between gap-3 px-5 py-5">
        <h2 id={titleId} className="text-base font-semibold text-apple-dark">{SLA_METRIC_LABELS[metric]}</h2>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold tabular-nums ${metric === 'initial_response' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>{filtered.length.toLocaleString('ko-KR')}건</span>
      </div>
      {filtered.length > 0 ? (
        <>
          <SlaViolationTableHeader label={SLA_METRIC_LABELS[metric]} sort={sort} widths={widths} onSort={setSort}
            onResize={(left, right, delta) => setWidths((current) => resizeSlaColumnWidths(current, left, right, delta))} />
          <ul>{filtered.map((ticket) => <TicketRow key={ticket.key} ticket={ticket} metric={metric} />)}</ul>
        </>
      ) : <p className="border-t border-apple-divider/70 px-5 py-12 text-center text-sm text-apple-mid">{isFiltered ? '선택한 필터에 맞는' : '해당 기간에 생성된'} {SLA_METRIC_LABELS[metric]} 티켓이 없습니다.</p>}
    </section>
  )
}
