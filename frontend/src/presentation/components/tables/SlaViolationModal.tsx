// frontend/src/presentation/components/tables/SlaViolationModal.tsx
import { useJira } from '@/app/context/JiraContext'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { MODAL_CLS } from '@/shared/ui'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'

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

export default function SlaViolationModal({ stage, issues, total, onClose }: Props) {
  const { jiraBrowse } = useJira()
  const badgeCls = STAGE_COLOR[stage] ?? 'bg-gray-100 text-gray-700 border-gray-200'

  return (
    <IssueModalShell
      title="SLA 위반 이슈 상세"
      subtitle={`전체 ${total}건`}
      onClose={onClose}
    >
      <div className="mb-4 flex items-center gap-2">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium border ${badgeCls}`}>
          {stage}
        </span>
        <span className="text-[12px] text-apple-light">위반 이슈 공뢡</span>
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
