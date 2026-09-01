// frontend/src/presentation/components/tables/WeeklyCreatedModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { CreatedIssue } from '@/domain/Dashboard'

interface Props {
  issues: CreatedIssue[]
  total: number
  title?: string
  dateRange?: { start: string; end: string }
  onClose: () => void
}

const COLUMNS: ColumnDef<CreatedIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><IssueTypeBadge type={d.type} /></div>, mobile: { slot: 'detail', render: d => <IssueTypeBadge type={d.type} /> } },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'detail', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시',  renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'secondary', render: d => d.created } },
]

export default function WeeklyCreatedModal({ issues, total, title = '생성 이슈', dateRange, onClose }: Props) {
  const subtitle = dateRange
    ? `${dateRange.start} – ${dateRange.end} · 전체 ${total}건 (생성일 최신순)`
    : `전체 ${total}건 (생성일 최신순)`

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
