// frontend/src/presentation/components/charts/SlaDonutChart.tsx
import { memo } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PIE_COLORS, CHART_HEIGHT, CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR } from '@/shared/constants'

export interface SlaViolationIssueForChart {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

export interface ViolationEntry {
  stage: string
  count: number
  rate: number
  issue_details?: SlaViolationIssueForChart[]
}

const STAGE_COLORS: Record<string, string> = {
  '최초 응답 SLA': '#f59e0b',
  '해결 시간 SLA': '#ef4444',
  '둘 다 위반':    '#8b5cf6',
}

interface Props {
  total: number
  distribution: ViolationEntry[]
  onSliceClick?: (entry: ViolationEntry) => void
}

function SlaDonutChart({ total, distribution, onSliceClick }: Props) {
  const data = distribution.map((d) => ({ name: d.stage, value: d.count }))

  if (total === 0 || data.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center" style={{ minHeight: CHART_HEIGHT }}>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">🎯 SLA 위반 분포</h3>
        <p className="text-sm text-gray-400">위반 없음</p>
      </div>
    )
  }

  const distSum = distribution.reduce((s, d) => s + d.count, 0)

  const handleClick = (chartData: { name: string }) => {
    if (!onSliceClick) return
    const found = distribution.find((d) => d.stage === chartData.name)
    if (found) onSliceClick(found)
  }

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">🎯 SLA 위반 분포</h3>
      <div className="relative">
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="45%"
              innerRadius={80}
              outerRadius={130}
              dataKey="value"
              label={({ percent }) => `${((percent ?? 0) * 100).toFixed(0)}%`}
              labelLine={false}
              onClick={onSliceClick ? handleClick : undefined}
              style={onSliceClick ? { cursor: 'pointer' } : undefined}
            >
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={STAGE_COLORS[entry.name] ?? PIE_COLORS[i % PIE_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: number, name: string) => {
                const entry = distribution.find((d) => d.stage === name)
                return [`${v}건 (${entry?.rate ?? 0}%)`, name]
              }}
            />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              iconType="circle"
              iconSize={CHART_LEGEND_ICON_SIZE}
              formatter={(value: string) => (
                <span
                  style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR, cursor: onSliceClick ? 'pointer' : 'default' }}
                  onClick={() => {
                    if (!onSliceClick) return
                    const found = distribution.find((d) => d.stage === value)
                    if (found) onSliceClick(found)
                  }}
                >
                  {value}
                </span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center mt-4">
            <p className="text-2xl font-bold text-gray-800">{distSum}</p>
            <p className="text-xs text-gray-400">이슈 단위 위반</p>
          </div>
        </div>
      </div>
      {onSliceClick && (
        <p className="text-center text-[11px] text-apple-light mt-1">영역을 클릭하면 상세 이슈를 확인할 수 있습니다</p>
      )}
    </div>
  )
}

export default memo(SlaDonutChart)
