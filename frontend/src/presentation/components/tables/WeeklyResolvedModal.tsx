// frontend/src/presentation/components/tables/WeeklyResolvedModal.tsx
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { ResolvedIssue } from '@/domain/Dashboard'

interface Props {
  issues: ResolvedIssue[]
  total: number
  title?: string
  dateRange?: { start: string; end: string }
  onClose: () => void
}

const COLUMNS: ColumnDef<ResolvedIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><IssueTypeBadge type={d.type} /></div>, mobile: { slot: 'detail', render: d => <IssueTypeBadge type={d.type} /> } },
  { header: '해결일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.resolved}</span>, mobile: { slot: 'secondary', render: d => d.resolved } },
]

export default function WeeklyResolvedModal({ issues, total, title = '완료 이슈', dateRange, onClose }: Props) {
  const subtitle = dateRange
    ? `${dateRange.start} – ${dateRange.end} · 전체 ${total}건 (해결일 최신순)`
    : `전체 ${total}건 (해결일 최신순)`

  return (
    <IssueTableModal
      title={title}
      subtitle={subtitle}
      data={issues}
      columns={COLUMNS}
      onClose={onClose}
    />
  )
}
