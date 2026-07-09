// frontend/src/presentation/components/charts/SlaDonutChart.tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PIE_COLORS, CHART_HEIGHT, CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR } from '@/shared/constants'

interface ViolationEntry {
  stage: string
  count: number
  rate: number
}

export default function SlaDonutChart({
  total,
  distribution,
}: {
  total: number
  distribution: ViolationEntry[]
}) {
  const data = distribution.map((d) => ({ name: d.stage, value: d.count }))

  if (total === 0 || data.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center" style={{ minHeight: CHART_HEIGHT }}>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">🎯 SLA 위반 분포</h3>
        <p className="text-sm text-gray-400">위반 없음</p>
      </div>
    )
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
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v, name) => [`${v}건`, name]} />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              iconType="circle"
              iconSize={CHART_LEGEND_ICON_SIZE}
              formatter={(value: string) => (
                <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center mt-4">
            <p className="text-2xl font-bold text-gray-800">{total}</p>
            <p className="text-xs text-gray-400">완료 위반</p>
          </div>
        </div>
      </div>
    </div>
  )
}
