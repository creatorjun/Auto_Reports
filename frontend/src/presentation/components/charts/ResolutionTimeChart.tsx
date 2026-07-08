// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { useConfig } from '@/infrastructure/hooks/useConfig'

interface IssueDetail {
  key: string
  summary: string
  type: string
  status: string
  stage_index: number
  created: string
  elapsed_days: number
}

const STATUS_COLORS: Record<string, string> = {
  '할 일':             '#94a3b8',
  '이슈 리뷰 중':      '#f59e0b',
  '연구소 대기 중':    '#8b5cf6',
  '연구소 검토 중':    '#6d28d9',
  '구현 중':          '#3b82f6',
  '배포 파일 검토 중': '#06b6d4',
  '자료 요청 중':    '#f97316',
  '결과 대기 중':    '#ef4444',
  '보류 중':          '#6b7280',
  '영업본부 검토중':  '#10b981',
}

const DEFAULT_COLOR = '#cbd5e1'

const ALL_STATUSES = [
  '할 일', '이슈 리뷰 중', '연구소 대기 중', '연구소 검토 중',
  '구현 중', '배포 파일 검토 중', '자료 요청 중', '결과 대기 중',
  '보류 중', '영업본부 검토중',
]

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? DEFAULT_COLOR
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-white font-medium"
      style={{ backgroundColor: color, fontSize: 10, whiteSpace: 'nowrap' }}
    >
      {status}
    </span>
  )
}

function ProcessTrack({ stageIndex }: { stageIndex: number }) {
  return (
    <div className="flex items-center gap-[2px]">
      {ALL_STATUSES.map((st, i) => {
        const color = STATUS_COLORS[st] ?? DEFAULT_COLOR
        const active = i === stageIndex
        return (
          <div
            key={st}
            title={st}
            className="rounded-sm transition-all"
            style={{
              width:  active ? 14 : 6,
              height: 10,
              backgroundColor: active ? color : '#e2e8f0',
              opacity: active ? 1 : 0.5,
            }}
          />
        )
      })}
    </div>
  )
}

export default function ResolutionTimeChart({ details }: { details: IssueDetail[] }) {
  const { data: config } = useConfig()
  const jiraBaseUrl = config?.jira_base_url?.replace(/\/$/, '') ?? ''

  if (!details?.length) return null

  const usedStatuses = [...new Set(details.map((d) => d.status))]

  const handleClick = (key: string) => {
    if (!jiraBaseUrl) return
    window.open(`${jiraBaseUrl}/browse/${key}`, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-apple-dark">📌 최근 이슈 현황 (최신 {details.length}건)</h3>
        <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end">
          {usedStatuses.map((st) => (
            <div key={st} className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: STATUS_COLORS[st] ?? DEFAULT_COLOR }}
              />
              <span style={{ fontSize: 10, color: '#86868b' }}>{st}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-[6px]">
        {details.map((d) => (
          <div
            key={d.key}
            onClick={() => handleClick(d.key)}
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors cursor-pointer hover:bg-blue-50 hover:shadow-sm"
            title={`${d.key} — Jira에서 열기`}
          >
            <span className="font-mono text-[10px] text-blue-500 hover:underline flex-shrink-0 w-[72px] truncate">
              {d.key}
            </span>

            <span className="text-[11px] text-apple-dark flex-1 truncate" title={d.summary}>
              {d.summary}
            </span>

            <ProcessTrack stageIndex={d.stage_index} />

            <StatusBadge status={d.status} />

            <span className="text-[10px] text-apple-light flex-shrink-0 w-[42px] text-right">
              {d.elapsed_days}일
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
