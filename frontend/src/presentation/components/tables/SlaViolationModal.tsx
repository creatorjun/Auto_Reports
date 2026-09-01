// frontend/src/presentation/components/tables/SlaViolationModal.tsx
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'

export interface SlaViolationIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

const STAGE_COLOR: Record<string, string> = {
  '최초 응답 SLA': 'bg-amber-100 text-amber-700 border-amber-200',
  '해결 시간 SLA': 'bg-red-100 text-red-700 border-red-200',
  '둘 다 위반':    'bg-purple-100 text-purple-700 border-purple-200',
}

interface Props {
  stage: string
  issues: SlaViolationIssue[]
  total: number
  onClose: () => void
}

const COLUMNS: ColumnDef<SlaViolationIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span>, mobile: { slot: 'primary', render: d => d.key } },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span>, mobile: { slot: 'summary', render: d => d.summary } },
  { header: '유형',      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span>, mobile: { slot: 'detail', render: d => d.type } },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div>, mobile: { slot: 'secondary', render: d => <StatusBadge status={d.status} /> } },
  { header: '생성일시', width: 'date', renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span>, mobile: { slot: 'detail', render: d => d.created } },
]

export default function SlaViolationModal({ stage, issues, total, onClose }: Props) {
  const badgeCls = STAGE_COLOR[stage] ?? 'bg-gray-100 text-gray-700 border-gray-200'

  return (
    <IssueTableModal
      title="SLA 위반 이슈 상세"
      subtitle={`전체 ${total}건`}
      data={issues}
      columns={COLUMNS}
      headerSlot={
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium border ${badgeCls}`}>
            {stage}
          </span>
          <span className="text-[12px] text-apple-light">위반 이슈 목록</span>
        </div>
      }
      onClose={onClose}
    />
  )
}
