// frontend/src/presentation/components/tables/ResultPendingModal.tsx
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { statusBadge } from './statusBadge'
import { MODAL_CLS } from '@/shared/ui'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'

export interface ResultPendingIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
  elapsed_days: number
}

interface Props {
  issues: ResultPendingIssue[]
  total: number
  onClose: () => void
}

export default function ResultPendingModal({ issues, total, onClose }: Props) {
  const { data: config } = useConfig()
  const jiraBase = `${config?.jira_base_url ?? 'https://seculayer.atlassian.net'}/browse`

  return (
    <IssueModalShell title="결과 대기 중" subtitle={`SLA 초과 후 결과 대기 · 전체 ${total}건 (오래된 순)`} size="lg" onClose={onClose}>
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-apple-divider/60">
              {['이슈 번호', '제목', '유형', '현재 상태', '생성일시', '경과일'].map(h => (
                <th key={h} className={MODAL_CLS.thCell}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {issues.map((d) => (
              <tr key={d.key} onClick={() => window.open(`${jiraBase}/${d.key}`, '_blank', 'noreferrer')} className="hover:bg-apple-gray/50 transition-colors duration-150 cursor-pointer">
                <td className={MODAL_CLS.keyCell}>{d.key}</td>
                <td className={MODAL_CLS.bodyCell}>{d.summary}</td>
                <td className={MODAL_CLS.metaCell}>{d.type}</td>
                <td className="py-2.5 whitespace-nowrap pr-4">{statusBadge(d.status)}</td>
                <td className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.created}</td>
                <td className="py-2.5 whitespace-nowrap">
                  <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="md:hidden divide-y divide-apple-divider/40">
        {issues.map((d) => (
          <div key={d.key} onClick={() => window.open(`${jiraBase}/${d.key}`, '_blank', 'noreferrer')} className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors">
            <div className="flex items-center justify-between">
              <span className={MODAL_CLS.keyCell}>{d.key}</span>
              <span className={MODAL_CLS.elapsedCell}>{d.elapsed_days}일 경과</span>
            </div>
            <p className="text-ui-sm text-apple-dark/80 leading-snug">{d.summary}</p>
            <div className="flex flex-wrap gap-2 items-center text-ui-xs text-apple-light">
              <span>{d.type}</span><span>·</span>{statusBadge(d.status)}<span>·</span><span>{d.created}</span>
            </div>
          </div>
        ))}
      </div>
    </IssueModalShell>
  )
}
