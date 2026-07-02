import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#3b82f6','#f59e0b','#ef4444','#8b5cf6','#10b981','#f97316']

export default function ReasonPieChart({ breakdown }: { breakdown: Record<string, number> }) {
  const data = Object.entries(breakdown).map(([name, value]) => ({ name, value }))
  if (!data.length) return null
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">🥧 SLA 지연 사유</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={80}
            dataKey="value"
            label={({ name, percent }) => `${name} ${Math.round(percent * 100)}%`}
          >
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v) => [`${v}건`]} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
