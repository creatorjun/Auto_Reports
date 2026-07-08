// frontend/src/presentation/components/charts/TypeBarChart.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#3b82f6', '#f59e0b', '#ef4444', '#10b981']

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

export default function TypeBarChart({ byType }: { byType: Record<string, ResolutionTypeEntry> }) {
  const data = Object.entries(byType).map(([name, d]) => ({ name, avg_days: d.avg_days, count: d.count }))
  if (!data.length) return null
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⏱️ 유형별 평균 처리일</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} unit="일" />
          <Tooltip formatter={(v) => [`${v}일`]} />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={7}
            payload={data.map((d, i) => ({ value: d.name, type: 'circle', color: COLORS[i % COLORS.length] }))}
            formatter={(value: string) => (
              <span style={{ fontSize: 11, color: '#86868b' }}>
                {value.length > 10 ? value.slice(0, 10) + '\u2026' : value}
              </span>
            )}
          />
          <Bar dataKey="avg_days" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
