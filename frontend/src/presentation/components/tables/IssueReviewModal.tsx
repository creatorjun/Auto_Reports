// frontend/src/presentation/components/tables/IssueReviewModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { ReviewIssue } from '@/domain/Dashboard'

interface Props {
  issues: ReviewIssue[]
  total: number
  onClose: () => void
}

const COLUMNS: ColumnDef<ReviewIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><IssueTypeBadge type={d.type} /></div>, mobile: { slot: 'detail', render: d => <IssueTypeBadge type={d.type} /> } },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'detail', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
  { header: '경과일',    renderCell: d => <div className="py-2.5 whitespace-nowrap"><span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span></div>, mobile: { slot: 'secondary', render: d => <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span> } },
]

export default function IssueReviewModal({ issues, total, onClose }: Props) {
  return (
    <IssueTableModal
      title="이슈 리뷰 중"
      subtitle={`SLA 초과 후 리뷰 대기 · 전체 ${total}건 (오래된 순)`}
      data={issues}
      columns={COLUMNS}
      onClose={onClose}
    />
  )
}
