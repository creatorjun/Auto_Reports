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
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span> },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span> },
  { header: '유형',      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span> },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div> },
  { header: '생성일시',  renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span> },
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
      renderMobileRow={(d) => (
        <div className="flex flex-col gap-1 px-2 py-3">
          <div className="flex items-center justify-between">
            <span className={MODAL_CLS.keyCell}>{d.key}</span>
            <StatusBadge status={d.status} />
          </div>
          <p className="truncate text-ui-sm text-apple-dark/80">{d.summary}</p>
          <div className="flex flex-wrap gap-2 items-center text-ui-xs text-apple-light">
            <span>{d.type}</span><span>·</span><span>{d.created}</span>
          </div>
        </div>
      )}
      onClose={onClose}
    />
  )
}
