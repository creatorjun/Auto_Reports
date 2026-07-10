// frontend/src/presentation/components/tables/SlaDelayModal.tsx
import { useJira } from '@/app/context/JiraContext'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { MODAL_CLS } from '@/shared/ui'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import type { SlaDelayIssue } from '@/presentation/components/charts/ReasonPieChart'

interface Props {
  status: string
  issues: SlaDelayIssue[]
  total: number
  onClose: () => void
}

export default function SlaDelayModal({ status, issues, total, onClose }: Props) {
  const { jiraBrowse } = useJira()

  return (
    <IssueModalShell
      title="SLA 지연 사유 상세"
      subtitle={`현재 상태: ${status} · 전체 ${total}건`}
      onClose={onClose}
    >
      <div className="mb-4">
        <StatusBadge status={status} />
      </div>

      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-apple-divider/60">
              {['이슈 번호', '제목', '유형', '현재 상태', '생성일시'].map((h) => (
                <th key={h} className={MODAL_CLS.thCell}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {issues.map((d) => (
              <tr
                key={d.key}
                onClick={() => window.open(`${jiraBrowse}/${d.key}`, '_blank', 'noreferrer')}
                className="hover:bg-apple-gray/50 transition-colors duration-150 cursor-pointer"
              >
                <td className={MODAL_CLS.keyCell}>{d.key}</td>
                <td className={MODAL_CLS.bodyCell}>{d.summary}</td>
                <td className={MODAL_CLS.metaCell}>{d.type}</td>
                <td className="py-2.5 whitespace-nowrap pr-4"><StatusBadge status={d.status} /></td>
                <td className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="md:hidden divide-y divide-apple-divider/40">
        {issues.map((d) => (
          <div
            key={d.key}
            onClick={() => window.open(`${jiraBrowse}/${d.key}`, '_blank', 'noreferrer')}
            className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className={MODAL_CLS.keyCell}>{d.key}</span>
              <StatusBadge status={d.status} />
            </div>
            <p className="text-ui-sm text-apple-dark/80 leading-snug">{d.summary}</p>
            <div className="flex flex-wrap gap-2 items-center text-ui-xs text-apple-light">
              <span>{d.type}</span><span>·</span><span>{d.created}</span>
            </div>
          </div>
        ))}
      </div>
    </IssueModalShell>
  )
}
