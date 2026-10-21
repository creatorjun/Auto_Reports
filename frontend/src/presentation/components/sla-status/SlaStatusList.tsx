// frontend/src/presentation/components/sla-status/SlaStatusList.tsx
import { useId, useState } from 'react'
import { ChevronDown, ExternalLink, PauseCircle, PlayCircle } from 'lucide-react'
import type { SlaStatusMetric, SlaStatusTicket } from '@/domain/SLAStatus'
import { slaPartnersLabel, slaVisibleStatusDurations } from '@/application/services/slaViolationReport'
import { useJira } from '@/presentation/context/JiraContext'
import { slaCreatedDate, slaDuration } from '@/presentation/utils/slaViolationFormatters'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import SlaStatusDurations from '@/presentation/components/sla-violations/SlaStatusDurations'

function percentLabel(percent: number): string {
  return percent > 0 && percent < 0.1 ? '0.1% 미만' : `${(Math.floor(percent * 10) / 10).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}%`
}

function MetricSummary({ sla }: { sla: SlaStatusMetric }) {
  const Icon = sla.paused ? PauseCircle : PlayCircle
  return (
    <div className="min-w-0 space-y-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-caption font-medium text-apple-dark">{sla.sla_name}</span><span className={`inline-flex items-center gap-1 text-caption ${sla.paused ? 'text-apple-mid' : 'text-red-600'}`}><Icon size={12} aria-hidden="true" />{sla.paused ? '일시정지' : '진행 중'}</span></div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 tabular-nums"><span className={`text-section-title font-semibold ${sla.remaining_percent < 10 ? 'text-red-600' : 'text-amber-700'}`}>{percentLabel(sla.remaining_percent)}</span><span className="text-label font-semibold text-apple-dark">{slaDuration(sla.remaining_millis)} 남음</span></div>
      <div role="meter" aria-label={`${sla.sla_name} 잔여 비율`} aria-valuenow={sla.remaining_percent} aria-valuemin={0} aria-valuemax={100} aria-valuetext={percentLabel(sla.remaining_percent)} className="h-1.5 overflow-hidden rounded-full bg-apple-divider/60"><div className={`h-full rounded-full ${sla.remaining_percent < 10 ? 'bg-red-500' : 'bg-amber-500'}`} style={{ width: `${Math.max(0, Math.min(100, sla.remaining_percent))}%` }} /></div>
    </div>
  )
}

function TicketRow({ ticket }: { ticket: SlaStatusTicket }) {
  const [expanded, setExpanded] = useState(false)
  const detailsId = useId()
  const { jiraBrowse } = useJira()
  const durations = ticket.status_durations_basis === 'resolution_sla' ? slaVisibleStatusDurations(ticket.status_durations ?? null) : null
  const longest = durations?.reduce<{ status: string; hours: number } | null>((selected, value) => !selected || value.hours > selected.hours ? value : selected, null)
  const details = [
    ['유형', ticket.issue_type], ['생성일', ticket.created_at ? slaCreatedDate(ticket.created_at) : null],
    ['생성 후 달력 경과일', ticket.elapsed_days == null ? null : `${ticket.elapsed_days.toLocaleString('ko-KR')}일`],
    ['고객사', ticket.customer], ['담당 파트너사', slaPartnersLabel(ticket.partners ?? null)],
    ['보고자', ticket.reporter], ['TAC 담당자', ticket.tac_assignee],
  ]
  return (
    <>
      <tr data-ticket-key={ticket.key} className="border-t border-apple-divider/60 align-top">
        <td className="px-4 py-4 sm:px-5"><a href={`${jiraBrowse}/${encodeURIComponent(ticket.key)}`} target="_blank" rel="noopener noreferrer" className="block rounded-lg focus-visible:outline-brand-500" aria-label={`${ticket.key} ${ticket.summary} · Jira 새 탭에서 열기`}><span className="inline-flex items-center gap-1.5 text-label font-semibold text-brand-600">{ticket.key}<ExternalLink size={12} aria-hidden="true" /></span><span className="mt-1.5 block break-words text-label font-medium leading-relaxed text-apple-dark">{ticket.summary}</span></a></td>
        <td className="px-4 py-4"><div className="space-y-4">{ticket.slas.map((sla) => <MetricSummary key={sla.sla_id} sla={sla} />)}</div></td>
        <td className="px-3 py-4"><StatusBadge status={ticket.status || '확인 불가'} size="md" /></td>
        <td className="break-words px-3 py-4 text-label text-apple-dark">{ticket.assignee || '미지정'}</td>
        <td className="px-3 py-4 text-label">{longest ? <><span className="block break-words text-apple-dark">{longest.status || '확인 불가'}</span><span className="mt-1 block font-semibold tabular-nums text-apple-mid">{slaDuration(longest.hours * 3_600_000)}</span></> : <span className="text-apple-mid">확인 불가</span>}</td>
        <td className="px-2 py-3"><button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} aria-controls={detailsId} aria-label={`${ticket.key} 상세 ${expanded ? '접기' : '펼치기'}`} className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray focus-visible:ring-2 focus-visible:ring-brand-500"><ChevronDown size={18} aria-hidden="true" className={expanded ? 'rotate-180' : ''} /></button></td>
      </tr>
      {expanded && <tr><td colSpan={6} className="px-4 pb-4 sm:px-5"><div id={detailsId} className="rounded-xl border border-apple-divider/60 bg-apple-gray p-4 sm:p-5">
        <h3 className="mb-3 text-section-label font-semibold text-apple-dark">SLA 목표·사용·잔여 시간</h3>
        <div className="grid gap-3 lg:grid-cols-2">{ticket.slas.map((sla) => <div key={sla.sla_id} className="rounded-xl border border-apple-divider/60 bg-apple-surface p-4"><p className="text-label font-semibold text-apple-dark">{sla.sla_name} <span className={`font-normal ${sla.paused ? 'text-apple-mid' : 'text-red-600'}`}>· {sla.paused ? '일시정지' : '진행 중'}</span></p><dl className="mt-3 grid grid-cols-3 gap-3">{[['목표', sla.goal_millis], ['사용', Math.max(0, sla.goal_millis - sla.remaining_millis)], ['잔여', sla.remaining_millis]].map(([label, value]) => <div key={label}><dt className="text-caption text-apple-mid">{label}</dt><dd className="mt-1 text-label font-semibold tabular-nums text-apple-dark">{slaDuration(Number(value))}</dd></div>)}</dl></div>)}</div>
        <div className="mt-5 border-t border-apple-divider/60 pt-4"><h3 className="mb-3 text-section-label font-semibold text-apple-dark">상태별 체류시간</h3>{ticket.status_durations_basis === 'resolution_sla' ? <SlaStatusDurations durations={ticket.status_durations ?? null} basis="resolution_sla" /> : <p className="text-caption text-apple-mid">상태별 SLA 시간을 확인할 수 없습니다.</p>}{ticket.status_duration_calendar && <p className="mt-2 text-caption text-apple-mid">적용 달력: {ticket.status_duration_calendar}</p>}</div>
        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-apple-divider/60 pt-4 lg:grid-cols-3">{details.map(([label, value]) => <div key={label}><dt className="text-caption text-apple-mid">{label}</dt><dd className="mt-1 break-words text-label text-apple-dark">{value || '확인 불가'}</dd></div>)}</dl>
        {!!ticket.warnings?.length && <div className="mt-4 text-caption text-amber-700"><p className="font-medium">일부 상세 정보 확인 필요</p><ul className="mt-1 space-y-1">{ticket.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>}
      </div></td></tr>}
    </>
  )
}

export default function SlaStatusList({ tickets, isFiltered }: { tickets: SlaStatusTicket[]; isFiltered: boolean }) {
  return (
    <section id="sla-status-results" aria-label="SLA 현황 검색 결과" className="min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm">
      {tickets.length === 0 ? <div className="px-6 py-14 text-center"><h2 className="text-section-title font-semibold text-apple-dark">{isFiltered ? '선택한 조건에 맞는 티켓이 없습니다.' : '잔여 30% 미만인 SLA 티켓이 없습니다.'}</h2><p className="mt-2 text-label text-apple-mid">{isFiltered ? '검색어나 필터를 변경해 주세요.' : '이미 SLA를 위반한 티켓은 SLA 위반 화면에서 확인할 수 있습니다.'}</p></div> : <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="SLA 현황 티켓 표, 좁은 화면에서는 가로로 스크롤"><table className="w-full min-w-[960px] table-fixed text-left"><caption className="sr-only">티켓별 SLA 잔여율과 잔여시간, 현재 상태, 담당자, 최대 체류 단계</caption><thead className="bg-apple-gray text-caption font-medium text-apple-mid"><tr><th scope="col" className="w-[26%] px-4 py-3 sm:px-5">티켓</th><th scope="col" className="w-[29%] px-4 py-3">SLA 잔여율 · 잔여시간</th><th scope="col" className="w-[13%] px-3 py-3">현재 상태</th><th scope="col" className="w-[11%] px-3 py-3">담당자</th><th scope="col" title="해결시간 SLA 기준" className="w-[16%] px-3 py-3">최대 체류 단계</th><th scope="col" className="w-[5%]"><span className="sr-only">상세</span></th></tr></thead><tbody>{tickets.map((ticket) => <TicketRow key={ticket.key} ticket={ticket} />)}</tbody></table></div>}
    </section>
  )
}
