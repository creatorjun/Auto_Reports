// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { ValueType, NameType } from 'recharts/types/component/DefaultTooltipContent'
import type { Payload } from 'recharts/types/component/DefaultTooltipContent'

interface RecentIssue {
  key: string
  summary: string
  type: string
  status: string
  stage_index: number
  created: string
  elapsed_days: number
}

interface Props {
  details: RecentIssue[]
}

const STATUS_COLORS: Record<string, string> = {
  '이슈 리뷰 중': '#f59e0b',
  '자료 요청 중': '#3b82f6',
  '결과 대기 중': '#8b5cf6',
  '처리 중':      '#22c55e',
  '기타':         '#6b7280',
}

function getColor(status: string): string {
  return STATUS_COLORS[status] ?? '#6b7280'
}

function tooltipFormatter(
  value: ValueType,
  _name: NameType,
  item: Payload<ValueType, NameType>,
): [string, string] {
  const payload = item.payload as { summary?: string; status?: string } | undefined
  const summary = payload?.summary ?? ''
  const status  = payload?.status  ?? ''
  return [`${value}일`, `${summary} [${status}]`]
}

export default function ResolutionTimeChart({ details }: Props) {
  if (!details || details.length === 0) {
    return (
      <div className="card flex items-center justify-center h-48 text-apple-light text-[13px]">
        최근 이슈 데이터가 없습니다.
      </div>
    )
  }

  const chartData = details.slice(0, 30).map((issue) => ({
    key:          issue.key,
    summary:      issue.summary,
    elapsed_days: issue.elapsed_days,
    status:       issue.status,
  }))

  return (
    <div className="card">
      <div className="mb-3">
        <h3 className="text-[13px] font-semibold text-apple-primary">
          📌 최근 이슈 현황 <span className="text-apple-light font-normal">(최신 50건)</span>
        </h3>
        <p className="text-[11px] text-apple-light mt-0.5">경과일 기준 상위 30건 시각화</p>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--color-divider)" />
          <XAxis
            type="number"
            dataKey="elapsed_days"
            tick={{ fontSize: 11, fill: 'var(--color-light)' }}
            label={{ value: '경과일', position: 'insideBottomRight', offset: -4, fontSize: 11, fill: 'var(--color-light)' }}
          />
          <YAxis
            type="category"
            dataKey="key"
            width={80}
            tick={{ fontSize: 10, fill: 'var(--color-light)' }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-card)',
              border: '1px solid var(--color-divider)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={tooltipFormatter}
          />
          <Bar dataKey="elapsed_days" radius={[0, 4, 4, 0]} maxBarSize={16}>
            {chartData.map((entry) => (
              <Cell key={entry.key} fill={getColor(entry.status)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
