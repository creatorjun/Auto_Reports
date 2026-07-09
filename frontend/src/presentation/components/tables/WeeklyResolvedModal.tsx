// frontend/src/presentation/components/tables/WeeklyResolvedModal.tsx
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { MODAL_CLS } from '@/shared/ui'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'

export interface ResolvedIssue {
  key: string
  summary: string
  type: string
  resolved: string
}

interface Props {
  issues: ResolvedIssue[]
  total: number
  dateRange?: { start: string; end: string }
  onClose: () => void
}

export default function WeeklyResolvedModal({ issues, total, dateRange, onClose }: Props) {
  const { data: config } = useConfig()
  const jiraBase = `${config?.jira_base_url ?? 'https://seculayer.atlassian.net'}/browse`

  const subtitle = dateRange
    ? `${dateRange.start} – ${dateRange.end} · 전체 ${total}건 (완료일 최신순)`
    : `전체 ${total}건 (완료일 최신순)`

  return (
    <IssueModalShell title="완료 이슈" subtitle={subtitle} onClose={onClose}>
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-apple-divider/60">
              {['이슈 번호', '제목', '유형', '완료일시'].map(h => (
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
                <td className={MODAL_CLS.metaCell + ' tabular-nums'}>{d.resolved || '—'}</td>
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
              <span className="text-ui-xs text-apple-light tabular-nums">{d.resolved || '—'}</span>
            </div>
            <p className="text-ui-sm text-apple-dark/80 leading-snug">{d.summary}</p>
            <span className="text-ui-xs text-apple-light">{d.type}</span>
          </div>
        ))}
      </div>
    </IssueModalShell>
  )
}
