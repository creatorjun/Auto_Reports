// frontend/src/presentation/components/tables/WeeklyResolvedModal.tsx
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import IssueTableModal, { type ColumnDef } from '@/presentation/components/common/IssueTableModal'
import { MODAL_CLS } from '@/presentation/config/ui'
import type { ResolvedIssue } from '@/domain/Dashboard'

interface Props {
  issues: ResolvedIssue[]
  total: number
  title?: string
  dateRange?: { start: string; end: string }
  onClose: () => void
}

const COLUMNS: ColumnDef<ResolvedIssue>[] = [
  { header: '이슈 번호',  renderCell: d => <span className={MODAL_CLS.keyCell}>{d.key}</span> },
  { header: '제목',      renderCell: d => <span className={MODAL_CLS.bodyCell}>{d.summary}</span> },
  { header: '유형',      renderCell: d => <div className="py-2.5 whitespace-nowrap pr-4"><IssueTypeBadge type={d.type} /></div> },
  { header: '해결일시',  renderCell: d => <span className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.resolved}</span> },
]

export default function WeeklyResolvedModal({ issues, total, title = '완료 이슈', dateRange, onClose }: Props) {
  const subtitle = dateRange
    ? `${dateRange.start} – ${dateRange.end} · 전체 ${total}건 (해결일 최신순)`
    : `전체 ${total}건 (해결일 최신순)`

  return (
    <IssueTableModal
      title={title}
      subtitle={subtitle}
      data={issues}
      columns={COLUMNS}
      renderMobileRow={(d, jiraBrowse) => (
        <div key={d.key} onClick={() => window.open(`${jiraBrowse}/${d.key}`, '_blank', 'noreferrer')} className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors">
          <div className="flex items-center justify-between">
            <span className={MODAL_CLS.keyCell}>{d.key}</span>
            <span className="text-ui-xs text-apple-light tabular-nums">{d.resolved}</span>
          </div>
          <p className="text-ui-sm text-apple-dark/80 leading-snug">{d.summary}</p>
          <div><IssueTypeBadge type={d.type} /></div>
        </div>
      )}
      onClose={onClose}
    />
  )
}
