import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#3b82f6','#f59e0b','#ef4444','#10b981']

export default function TypeBarChart({ breakdown }: { breakdown: Record<string, { avg_days: number; count: number }> }) {
  const data = Object.entries(breakdown).map(([name, d]) => ({ name, avg_days: d.avg_days, count: d.count }))
  if (!data.length) return null
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⏱️ 유형별 평균 처리일</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} unit="일" />
          <Tooltip formatter={(v) => [`${v}일`]} />
          <Bar dataKey="avg_days" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
