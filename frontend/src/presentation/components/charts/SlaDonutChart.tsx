// frontend/src/presentation/components/charts/SlaDonutChart.tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6']

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
      <div className="card flex flex-col items-center justify-center" style={{ minHeight: 240 }}>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">🎯 SLA 위반 분포</h3>
        <p className="text-sm text-gray-400">위반 없음</p>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">🎯 SLA 위반 분포</h3>
      <div className="relative">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="45%"
              innerRadius={60}
              outerRadius={90}
              dataKey="value"
              label={({ percent }) =>
                `${((percent ?? 0) * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v, name) => [`${v}건`, name]} />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              iconType="circle"
              iconSize={7}
              formatter={(value: string) => (
                <span style={{ fontSize: 11, color: '#86868b' }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center mt-4">
            <p className="text-2xl font-bold text-gray-800">{total}</p>
            <p className="text-xs text-gray-400">총 위반</p>
          </div>
        </div>
      </div>
    </div>
  )
}