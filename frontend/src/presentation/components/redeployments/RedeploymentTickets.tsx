// frontend/src/presentation/components/redeployments/RedeploymentTickets.tsx
import { Fragment, useEffect, useState } from 'react'
import { ChevronDown, ExternalLink } from 'lucide-react'
import type { RedeploymentColumn, RedeploymentColumnFilters, RedeploymentTicket } from '@/domain/RedeploymentReport'
import ColumnSearchInput from '@/presentation/components/common/ColumnSearchInput'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { useJira } from '@/presentation/context/JiraContext'

const columns: { key: RedeploymentColumn; label: string }[] = [
  { key: 'ticket', label: '번호 / 제목' },
  { key: 'issue_type', label: '유형' },
  { key: 'status', label: '현재 상태' },
  { key: 'cause', label: '재배포 원인' },
  { key: 'repatch_count', label: '재패치' },
  { key: 'completion_month', label: '완료 월' },
]

interface Props {
  tickets: RedeploymentTicket[]
  columnFilters?: RedeploymentColumnFilters
  onColumnFilterChange?: (column: RedeploymentColumn, value: string) => void
  paginationResetKey?: string
}

function dateLabel(value: string | null) {
  if (!value) return '미입력'
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' }).format(new Date(value))
}

export default function RedeploymentTickets({ tickets, columnFilters = {}, onColumnFilterChange, paginationResetKey }: Props) {
  const { jiraBrowse } = useJira()
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(0)
  useEffect(() => { setPage(0) }, [paginationResetKey])
  const pages = Math.max(1, Math.ceil(tickets.length / 25))
  const activePage = Math.min(page, pages - 1)
  const toggle = (key: string) => setExpanded((current) => {
    const next = new Set(current)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    return next
  })
  return <>
    {onColumnFilterChange && <div className="mb-4 grid grid-cols-2 gap-3 lg:hidden">
      {columns.map(({ key, label }) => <label key={key} className="min-w-0 text-caption font-medium text-apple-mid">{label}
        <ColumnSearchInput label={label} value={columnFilters[key] ?? ''} mobile onChange={(value) => onColumnFilterChange(key, value)} />
      </label>)}
    </div>}
    <div className="overflow-x-auto rounded-xl border border-apple-divider">
      <table className="w-full min-w-[1040px] text-left">
        <thead className="bg-apple-gray text-caption font-semibold text-apple-mid"><tr>
          {columns.map(({ key, label }) => <th scope="col" key={key} className="px-4 py-3 whitespace-nowrap">{label}
            {onColumnFilterChange && <div className="hidden lg:block"><ColumnSearchInput label={label} value={columnFilters[key] ?? ''} onChange={(value) => onColumnFilterChange(key, value)} /></div>}
          </th>)}
          <th scope="col" className="px-4 py-3 whitespace-nowrap">상세</th>
        </tr></thead>
        <tbody className="divide-y divide-apple-divider">
          {tickets.slice(activePage * 25, (activePage + 1) * 25).map((ticket) => <Fragment key={ticket.key}>
            <tr className="align-top hover:bg-apple-gray/40">
              <td className="w-[34%] min-w-[280px] px-4 py-4"><a href={`${jiraBrowse}/${encodeURIComponent(ticket.key)}`} target="_blank" rel="noopener noreferrer" className="group block rounded focus-visible:outline-brand-500">
                <span className="inline-flex items-center gap-1 text-caption font-semibold text-brand-600">{ticket.key}<ExternalLink size={13} /></span>
                <span className="mt-1 block text-label font-medium text-apple-dark group-hover:underline">{ticket.summary}</span>
              </a><span className="mt-1 block text-caption text-apple-light">{ticket.customer || '고객사 미입력'}</span></td>
              <td className="px-4 py-4"><IssueTypeBadge type={ticket.issue_type} /></td>
              <td className="px-4 py-4"><StatusBadge status={ticket.status} /></td>
              <td className="min-w-[200px] px-4 py-4"><span className="text-label font-medium text-apple-dark">{ticket.cause || '원인 미입력'}</span><p className="mt-1 line-clamp-2 max-w-sm break-words text-caption text-apple-mid">{ticket.reason || '상세 사유 미입력'}</p></td>
              <td className="px-4 py-4 text-label tabular-nums text-apple-dark">{ticket.repatch_count === null ? <span className="text-caption text-apple-light">미입력</span> : `${ticket.repatch_count}회`}</td>
              <td className="px-4 py-4 text-caption text-apple-mid whitespace-nowrap">{ticket.closed ? ticket.completion_month || '미입력' : '진행 중'}</td>
              <td className="px-3 py-3"><button type="button" aria-expanded={expanded.has(ticket.key)} aria-controls={`redeployment-${ticket.key}`} aria-label={`${ticket.key} 상세 ${expanded.has(ticket.key) ? '접기' : '펼치기'}`} onClick={() => toggle(ticket.key)} className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray focus-visible:ring-2 focus-visible:ring-brand-500"><ChevronDown size={18} className={expanded.has(ticket.key) ? 'rotate-180' : ''} /></button></td>
            </tr>
            {expanded.has(ticket.key) && <tr id={`redeployment-${ticket.key}`}><td colSpan={7} className="bg-apple-gray/40 px-5 py-5">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-caption md:grid-cols-4">
                {[
                  ['고객사', ticket.customer || '미입력'], ['파트너사', ticket.partners.join(', ') || '본사'],
                  ['담당자', ticket.assignee || '미지정'], ['보고자', ticket.reporter || '미지정'],
                  ['생성일', dateLabel(ticket.created_at)], ['해결일', dateLabel(ticket.resolved_at)],
                  ['배포 완료 월', ticket.completion_month || '미입력'], ['재배포 원인', ticket.cause || '미입력'],
                ].map(([label, value]) => <div key={label}><dt className="text-apple-mid">{label}</dt><dd className="mt-1 break-words font-medium text-apple-dark">{value}</dd></div>)}
              </dl>
              <div className="mt-4 border-t border-apple-divider pt-4"><h3 className="text-label font-semibold text-apple-dark">재배포 상세 사유</h3><p className="mt-2 whitespace-pre-wrap break-words text-label leading-relaxed text-apple-mid">{ticket.reason || 'Jira에 상세 사유가 입력되지 않았습니다.'}</p></div>
            </td></tr>}
          </Fragment>)}
          {tickets.length === 0 && <tr><td colSpan={7} className="p-10 text-center text-label text-apple-mid">조건에 맞는 재배포 티켓이 없습니다.</td></tr>}
        </tbody>
      </table>
    </div>
    {pages > 1 && <div className="mt-4 flex items-center justify-end gap-3 text-control text-apple-mid"><button disabled={activePage === 0} onClick={() => setPage(activePage - 1)} className="rounded-lg border border-apple-divider px-3 py-2 disabled:opacity-40">이전</button><span>{activePage + 1} / {pages}</span><button disabled={activePage + 1 >= pages} onClick={() => setPage(activePage + 1)} className="rounded-lg border border-apple-divider px-3 py-2 disabled:opacity-40">다음</button></div>}
  </>
}
