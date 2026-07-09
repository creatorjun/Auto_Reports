// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { useState } from 'react'
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { STATUS_STYLE, STATUS_LEGEND, STAGE_TOTAL } from '@/shared/ui'
import type { RecentIssue } from '@/presentation/pages/DashboardPage'

const PAGE_SIZE = 50

interface Props {
  details: RecentIssue[]
}

function getStatusStyle(status: string) {
  return STATUS_STYLE[status] ?? { bg: 'bg-status-todo', text: 'text-white' }
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
  const [page, setPage] = useState(1)

  if (!details || details.length === 0) {
    return (
      <div className="card flex items-center justify-center h-48 text-apple-light text-ui-base">
        최근 이슈 데이터가 없습니다.
      </div>
    )
  }

  const totalPages = Math.ceil(details.length / PAGE_SIZE)
  const pageItems = details.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-ui-md font-semibold text-apple-primary">
          📌 최근 이슈 현황{' '}
          <span className="text-apple-light font-normal">(최신 {details.length}건)</span>
        </h3>
        <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end">
          {STATUS_LEGEND.map((l) => (
            <span key={l.label} className="flex items-center gap-1 text-ui-sm text-apple-light">
              <span className={`inline-block w-2 h-2 rounded-full ${l.color}`} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-ui-base">
          <thead>
            <tr className="border-b border-apple-divider text-ui-sm text-apple-light">
              <th className="pb-1.5 pr-3 text-left font-medium whitespace-nowrap">이슈</th>
              <th className="pb-1.5 pr-4 text-left font-medium">제목</th>
              <th className="pb-1.5 pr-3 text-left font-medium whitespace-nowrap">진행 상태</th>
              <th className="pb-1.5 pr-3 text-left font-medium whitespace-nowrap">보고자</th>
              <th className="pb-1.5 pr-3 text-left font-medium whitespace-nowrap">담당자</th>
              <th className="pb-1.5 text-right font-medium whitespace-nowrap">경과</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((issue) => {
              const style = getStatusStyle(issue.status)
              const jiraUrl = `${jiraBaseUrl}/browse/${issue.key}`
              return (
                <tr
                  key={issue.key}
                  onClick={() => window.open(jiraUrl, '_blank', 'noreferrer')}
                  className="border-b border-apple-divider last:border-0 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors cursor-pointer"
                >
                  <td className="py-2 pr-3 whitespace-nowrap font-mono text-ui-sm text-blue-500">
                    {issue.key}
                  </td>
                  <td className="py-2 pr-4 text-apple-primary max-w-[360px] truncate">
                    {issue.summary}
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex items-center gap-2">
                      <StageBar stageIndex={issue.stage_index} />
                      <span className={`inline-block px-2 py-0.5 rounded-full text-ui-sm font-medium ${style.bg} ${style.text} whitespace-nowrap`}>
                        {issue.status}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span className="text-ui-sm text-apple-light">{issue.reporter}</span>
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span className="text-ui-sm text-apple-light">{issue.tac_team}</span>
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

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-apple-divider">
          <span className="text-ui-sm text-apple-light">
            {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, details.length)} / {details.length}건
          </span>
          <div className="flex gap-1">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => setPage(i + 1)}
                className={`px-3 py-1 rounded text-ui-sm font-medium transition-colors ${
                  page === i + 1
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-100 text-apple-mid hover:bg-gray-200'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
