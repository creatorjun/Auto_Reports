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
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span> },
  { header: '제목', width: 'wide', renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span> },
  { header: '유형',      renderCell: d => <span className={MODAL_CLS.metaCell}>{d.type}</span> },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div> },
  { header: '생성일시',  renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span> },
  { header: '경과일',    renderCell: d => <div className="py-2.5 whitespace-nowrap"><span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span></div> },
]

export default function IncompleteIssueModal({ issues, total, title = '미완료 이슈', onClose }: Props) {
  return (
    <IssueTableModal
      title={title}
      subtitle={`처리 완료되지 않은 이슈 · 전체 ${total}건 (오래된 순)`}
      data={issues}
      columns={COLUMNS}
      paginate
      renderMobileRow={(d) => (
        <div className="flex flex-col gap-1 px-2 py-3">
          <div className="flex items-center justify-between">
            <span className={MODAL_CLS.keyCell}>{d.key}</span>
            <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span>
          </div>
          <p className="truncate text-ui-sm text-apple-dark/80">{d.summary}</p>
          <div className="flex flex-wrap gap-2 items-center text-ui-xs text-apple-light">
            <span>{d.type}</span><span>·</span><StatusBadge status={d.status} /><span>·</span><span>{d.created}</span>
          </div>
        </div>
      )}
      onClose={onClose}
    />
  )
}
