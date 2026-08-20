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
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span> },
  { header: '제목',      renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span> },
  { header: '유형',      renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><IssueTypeBadge type={d.type} /></div> },
  { header: '현재 상태',  renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></div> },
  { header: '생성일시',  renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</span> },
  { header: '경과일',    renderCell: d => <div className="py-2.5 whitespace-nowrap"><span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span></div> },
]

export default function IssueReviewModal({ issues, total, onClose }: Props) {
  return (
    <IssueTableModal
      title="이슈 리뷰 중"
      subtitle={`SLA 초과 후 리뷰 대기 · 전체 ${total}건 (오래된 순)`}
      data={issues}
      columns={COLUMNS}
      renderMobileRow={(d, jiraBrowse) => (
        <div key={d.key} onClick={() => window.open(`${jiraBrowse}/${d.key}`, '_blank', 'noreferrer')} className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors">
          <div className="flex items-center justify-between">
            <span className={MODAL_CLS.keyCell}>{d.key}</span>
            <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span>
          </div>
          <p className="text-ui-sm text-apple-dark/80 leading-snug">{d.summary}</p>
          <div className="flex flex-wrap gap-2 items-center text-ui-xs text-apple-light">
            <IssueTypeBadge type={d.type} /><span>·</span><StatusBadge status={d.status} /><span>·</span><span>{d.created}</span>
          </div>
        </div>
      )}
      onClose={onClose}
    />
  )
}
