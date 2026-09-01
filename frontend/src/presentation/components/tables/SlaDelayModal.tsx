// frontend/src/presentation/components/tables/SlaDelayModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { SlaDelayIssue } from '@/domain/Dashboard'

interface Props {
  status: string
  issues: SlaDelayIssue[]
  total: number
  onClose: () => void
}

const COLUMNS: ColumnDef<SlaDelayIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span>, mobile: { slot: 'detail', render: d => d.type } },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'secondary', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
]

export default function SlaDelayModal({ status, issues, total, onClose }: Props) {
  return (
    <IssueTableModal
      title="SLA 지연 사유 상세"
      subtitle={`현재 상태: ${status} · 전체 ${total}건`}
      data={issues}
      columns={COLUMNS}
      headerSlot={<StatusBadge status={status} />}
      onClose={onClose}
    />
  )
}
