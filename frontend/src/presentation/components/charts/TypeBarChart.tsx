// frontend/src/presentation/components/charts/TypeBarChart.tsx
import { memo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { PIE_COLORS, CHART_HEIGHT, CHART_TICK_FONT_SIZE, CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR } from '@/shared/constants'

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

function TypeBarChart({ byType }: { byType: Record<string, ResolutionTypeEntry> }) {
  const data = Object.entries(byType).map(([name, d]) => ({ name, avg_days: d.avg_days, count: d.count }))
  if (!data.length) return null
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⏱️ 유형별 평균 처리일</h3>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: CHART_TICK_FONT_SIZE }} />
          <YAxis tick={{ fontSize: CHART_TICK_FONT_SIZE }} unit="일" />
          <Tooltip formatter={(v) => [`${v}일`]} />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={CHART_LEGEND_ICON_SIZE}
            payload={data.map((d, i) => ({ value: d.name, type: 'circle', color: PIE_COLORS[i % PIE_COLORS.length] }))}
            formatter={(value: string) => (
              <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>
                {value.length > 10 ? value.slice(0, 10) + '…' : value}
              </span>
            )}
          />
          <Bar dataKey="avg_days" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(TypeBarChart)
