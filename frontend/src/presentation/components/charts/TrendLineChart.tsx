// frontend/src/presentation/components/charts/TrendLineChart.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { CHART_COLORS } from '@/presentation/config/ui'
import { CHART_LEGEND_COLOR, MONTHLY_COUNT_COLORS } from '@/presentation/config/constants'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'

interface Props {
  created: number
  resolved: number
  periodLabel?: string
  onBarClick?: (key: '생성' | '해결') => void
}

export default function TrendLineChart({ created, resolved, onBarClick, periodLabel = '이번 주' }: Props) {
  const exportMode = useDashboardExportMode()
  const data = [
    { name: periodLabel, '생성': created, '해결': resolved },
  ]

  return (
    <div data-pdf-kind="chart" className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⚖️ 생성 vs 해결</h3>
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={7}
            formatter={(value: string) => (
              <span
                style={{ fontSize: 11, color: CHART_LEGEND_COLOR, cursor: onBarClick ? 'pointer' : 'default' }}
                onClick={() => {
                  if (value === '생성' || value === '해결') onBarClick?.(value)
                }}
              >
                {value}
              </span>
            )}
          />
          <Bar
            isAnimationActive={!exportMode}
            dataKey="생성"
            fill={MONTHLY_COUNT_COLORS.created}
            radius={[6, 6, 0, 0]}
            style={onBarClick ? { cursor: 'pointer' } : undefined}
            onClick={() => onBarClick?.('생성')}
          />
          <Bar
            isAnimationActive={!exportMode}
            dataKey="해결"
            fill={MONTHLY_COUNT_COLORS.resolved}
            radius={[6, 6, 0, 0]}
            style={onBarClick ? { cursor: 'pointer' } : undefined}
            onClick={() => onBarClick?.('해결')}
          />
        </BarChart>
      </ResponsiveContainer>
      {!exportMode && onBarClick && (
        <p className="text-center text-[11px] text-apple-light mt-1">막대를 클릭하면 이슈 목록을 확인할 수 있습니다</p>
      )}
    </div>
  )
}
