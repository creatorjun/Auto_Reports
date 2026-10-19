// frontend/src/presentation/components/tables/ResultPendingModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { ResultPendingIssue } from '@/domain/Dashboard'

interface Props {
  issues: ResultPendingIssue[]
  total: number
  onClose: () => void
}

const COLUMNS: ColumnDef<ResultPendingIssue>[] = [
  { header: '이슈 번호', sortValue: d => d.key,  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', sortValue: d => d.summary, renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형', sortValue: d => d.type,      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span>, mobile: { slot: 'detail', render: d => d.type } },
  { header: '현재 상태', sortValue: d => d.status,  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'detail', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시', width: 'date', sortValue: d => d.created, sortType: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
  { header: '경과일', sortValue: d => d.elapsed_days, sortType: 'number',    renderCell: d => <div className="py-2.5 whitespace-nowrap"><span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span></div>, mobile: { slot: 'secondary', render: d => <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span> } },
]

export default function ResultPendingModal({ issues, total, onClose }: Props) {
  return (
    <IssueTableModal
      title="결과 대기 중"
      subtitle={`보고서 기간에 생성된 이슈 · 전체 ${total}건`}
      data={issues}
      columns={COLUMNS}
      onClose={onClose}
    />
  )
}
