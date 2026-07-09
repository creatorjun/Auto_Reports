// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { useConfig } from '@/infrastructure/hooks/useConfig'
import type { RecentIssue } from '@/presentation/pages/DashboardPage'

interface Props {
  details: RecentIssue[]
}

const STAGE_TOTAL = 7

const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  '할 일':              { bg: 'bg-gray-400',    text: 'text-white' },
  '재오픈':             { bg: 'bg-gray-400',    text: 'text-white' },
  '자료 요청 중':       { bg: 'bg-blue-500',    text: 'text-white' },
  '이슈 리뷰 중':       { bg: 'bg-amber-500',   text: 'text-white' },
  '연구소 대기 중':     { bg: 'bg-purple-500',  text: 'text-white' },
  '연구소 검토 중':     { bg: 'bg-violet-500',  text: 'text-white' },
  '구현 중':           { bg: 'bg-green-500',   text: 'text-white' },
  '배포 파일 검토 중':  { bg: 'bg-cyan-500',    text: 'text-white' },
  '결과 대기 중':       { bg: 'bg-red-500',     text: 'text-white' },
}

const LEGEND = [
  { label: '할 일 / 재오픈',      color: 'bg-gray-400' },
  { label: '자료 요청 중',        color: 'bg-blue-500' },
  { label: '이슈 리뷰 중',        color: 'bg-amber-500' },
  { label: '연구소 대기/검토 중', color: 'bg-purple-500' },
  { label: '구현 중',             color: 'bg-green-500' },
  { label: '배포 파일 검토 중',   color: 'bg-cyan-500' },
  { label: '결과 대기 중',        color: 'bg-red-500' },
]

function getStatusStyle(status: string) {
  return STATUS_STYLE[status] ?? { bg: 'bg-gray-400', text: 'text-white' }
}

function StageBar({ stageIndex }: { stageIndex: number }) {
  return (
    <div className="flex gap-[2px] items-center">
      {Array.from({ length: STAGE_TOTAL }).map((_, i) => (
        <div
          key={i}
          className={`h-[10px] w-[10px] rounded-[2px] ${
            i <= stageIndex ? 'bg-amber-400' : 'bg-gray-200 dark:bg-gray-700'
          }`}
        />
      ))}
    </div>
  )
}

export default function ResolutionTimeChart({ details }: Props) {
  const { data: config } = useConfig()
  const jiraBaseUrl = config?.jira_base_url ?? 'https://seculayer.atlassian.net'

  if (!details || details.length === 0) {
    return (
      <div className="card flex items-center justify-center h-48 text-apple-light text-[13px]">
        최근 이슈 데이터가 없습니다.
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-[14px] font-semibold text-apple-primary">
            📌 최근 이슈 현황{' '}
            <span className="text-apple-light font-normal">(최신 {details.length}건)</span>
          </h3>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end">
          {LEGEND.map((l) => (
            <span key={l.label} className="flex items-center gap-1 text-[12px] text-apple-light">
              <span className={`inline-block w-2 h-2 rounded-full ${l.color}`} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <tbody>
            {details.map((issue) => {
              const style = getStatusStyle(issue.status)
              const jiraUrl = `${jiraBaseUrl}/browse/${issue.key}`
              return (
                <tr
                  key={issue.key}
                  onClick={() => window.open(jiraUrl, '_blank', 'noreferrer')}
                  className="border-b border-apple-divider last:border-0 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors cursor-pointer"
                >
                  <td className="py-2 pr-3 whitespace-nowrap font-mono text-[12px] text-blue-500">
                    {issue.key}
                  </td>
                  <td className="py-2 pr-4 text-apple-primary max-w-[400px] truncate">
                    {issue.summary}
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex items-center gap-2">
                      <StageBar stageIndex={issue.stage_index} />
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[12px] font-medium ${style.bg} ${style.text} whitespace-nowrap`}
                      >
                        {issue.status}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span className="text-[12px] text-apple-light">
                      {issue.assignee}
                    </span>
                  </td>
                  <td className="py-2 text-right text-apple-light whitespace-nowrap">
                    {issue.elapsed_days}일
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
