// frontend/src/presentation/components/tables/IncompleteIssueModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { IncompleteIssue } from '@/domain/Dashboard'

interface Props {
  issues: IncompleteIssue[]
  total: number
  title?: string
  onClose: () => void
}

const COLUMNS: ColumnDef<IncompleteIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span>, mobile: { slot: 'detail', render: d => d.type } },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'detail', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
  { header: '경과일',    renderCell: d => <div className="py-2.5 whitespace-nowrap"><span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span></div>, mobile: { slot: 'secondary', render: d => <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span> } },
]

export default function IncompleteIssueModal({ issues, total, title = '미완료 이슈', onClose }: Props) {
  return (
    <IssueTableModal
      title={title}
      subtitle={`처리 완료되지 않은 이슈 · 전체 ${total}건 (오래된 순)`}
      data={issues}
      columns={COLUMNS}
      paginate
      onClose={onClose}
    />
  )
}
