// frontend/src/presentation/components/tables/SlaOverdueModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'

export interface OverdueIssue {
  key: string
  summary: string
  type: string
  created: string
  resp_status: string
  over_h: number
}

interface Props {
  issues: OverdueIssue[]
  total: number
  onClose: () => void
}

const COLUMNS: ColumnDef<OverdueIssue>[] = [
  { header: '이슈 번호', renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형', renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span>, mobile: { slot: 'detail', render: d => d.type } },
  { header: '생성일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
  { header: '현재 상태', renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.resp_status} /></div>, mobile: { slot: 'detail', render: d => <StatusBadge status={d.resp_status} /> } },
  { header: '초과시간', renderCell: d => <span className={MODAL_CLS.elapsedCell}>+{d.over_h}h</span>, mobile: { slot: 'secondary', render: d => <span className={MODAL_CLS.elapsedCell}>+{d.over_h}h</span> } },
]

export default function SlaOverdueModal({ issues, total, onClose }: Props) {
  return (
    <IssueTableModal
      title="SLA 초과 이슈 상세"
      subtitle={`30일 이상 미해결 이슈 · 총 ${total}건 (초과시간 내림차순)`}
      data={issues}
      columns={COLUMNS}
      onClose={onClose}
    />
  )
}
