// frontend/src/presentation/components/annual/AnnualIssueDetailsModal.tsx
import { useMemo, useState, type ReactNode } from 'react'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import type { ChartIssue } from '@/domain/ReportChartDetails'

export type AnnualDetailIssue = ChartIssue

interface Props {
  title: string
  total: number
  issues: AnnualDetailIssue[]
  description?: string
  dateField?: 'created' | 'resolved'
  headerSlot?: ReactNode
  onClose: () => void
}

const PAGE_SIZE = 20

export default function AnnualIssueDetailsModal({ title, total, issues, description, dateField, headerSlot, onClose }: Props) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const filtered = useMemo(() => {
    const keyword = search.trim().toLocaleLowerCase('ko-KR')
    return issues.filter((issue) => [issue.key, issue.summary, issue.type, issue.status, issue.cause, issue.assignee, ...(issue.partners ?? [])]
      .some((value) => value?.toLocaleLowerCase('ko-KR').includes(keyword)))
  }, [issues, search])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pages)
  const rows = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const hasResolved = dateField ? dateField === 'resolved' : issues.some((issue) => Boolean(issue.resolved))
  const columns: ColumnDef<AnnualDetailIssue>[] = [
    { header: '티켓', renderCell: (issue) => <span className="font-mono text-sm font-semibold text-brand-600">{issue.key}</span>, mobile: { slot: 'primary' } },
    { header: '제목', width: 'wide', renderCell: (issue) => <div className="py-3 text-left text-base whitespace-normal break-words" title={issue.summary}>{issue.summary}{(issue.cause || issue.assignee || issue.partners?.length) && <p className="mt-1 text-sm text-apple-mid">{[issue.cause, issue.assignee, issue.partners?.join(', ')].filter(Boolean).join(' · ')}</p>}</div>, mobile: { slot: 'summary' } },
    { header: '유형', renderCell: (issue) => <IssueTypeBadge type={issue.type} />, mobile: { slot: 'detail' } },
  ]
  if (issues.some((issue) => Boolean(issue.status))) {
    columns.push({ header: '상태', renderCell: (issue) => issue.status ? <StatusBadge status={issue.status} /> : '—', mobile: { slot: 'detail' } })
  }
  if (issues.some((issue) => typeof issue.sla_met === 'boolean')) {
    columns.push({ header: 'SLA', renderCell: (issue) => <span className="text-sm font-semibold">{issue.sla_met === true ? '준수' : issue.sla_met === false ? '위반' : '미확인'}</span>, mobile: { slot: 'detail' } })
  }
  if (issues.some((issue) => issue.elapsed_hours != null)) {
    columns.push({ header: '처리시간', renderCell: (issue) => <span className="text-sm tabular-nums">{issue.elapsed_hours == null ? '—' : `${issue.elapsed_hours.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}시간`}</span>, mobile: { slot: 'detail' } })
  }
  columns.push({ header: hasResolved ? '해결일시' : '생성일시', width: 'date', renderCell: (issue) => <span className="text-sm tabular-nums">{(hasResolved ? issue.resolved : issue.created)?.replace('T', ' ').slice(0, 16) || '—'}</span>, mobile: { slot: 'secondary' } })

  return (
    <div className="annual-issue-details">
    <IssueTableModal
      title={title}
      subtitle={`차트 집계 ${total.toLocaleString('ko-KR')}건 · 상세 목록 ${issues.length.toLocaleString('ko-KR')}건`}
      size="lg"
      data={rows}
      columns={columns}
      onClose={onClose}
      headerSlot={
        <div className="space-y-3 text-sm text-apple-dark">
          {description && <p>{description}</p>}
          {total !== issues.length && <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">차트 집계와 조회 가능한 상세 건수가 다릅니다. 목록은 확인된 이슈만 표시합니다.</p>}
          {headerSlot}
          <label className="block">
            <span className="mb-1 block font-medium">상세 이슈 검색</span>
            <input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="티켓, 제목, 유형, 상태" className="w-full rounded-lg border border-apple-divider bg-apple-surface px-3 py-2.5 text-base outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500" />
          </label>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span aria-live="polite">검색 결과 {filtered.length.toLocaleString('ko-KR')}건 · {currentPage} / {pages}페이지</span>
            <div className="flex gap-2">
              <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)} className="rounded-lg border border-apple-divider px-3 py-2 disabled:opacity-40">이전</button>
              <button type="button" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)} className="rounded-lg border border-apple-divider px-3 py-2 disabled:opacity-40">다음</button>
            </div>
          </div>
          {filtered.length === 0 && <p role="status" className="py-6 text-center text-apple-mid">{search ? '검색 조건에 맞는 이슈가 없습니다.' : total === 0 ? '해당 조건의 이슈가 없습니다.' : '조회 가능한 개별 이슈가 없습니다.'}</p>}
        </div>
      }
    />
    </div>
  )
}
