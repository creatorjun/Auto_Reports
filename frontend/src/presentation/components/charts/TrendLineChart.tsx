import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function TrendLineChart({ created, resolved }: { created: number; resolved: number }) {
  const data = [
    { name: '이번 주', '생성': created, '해결': resolved }
  ]
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⚖️ 생성 vs 해결</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="생성" fill="#3b82f6" radius={[6, 6, 0, 0]} />
          <Bar dataKey="해결" fill="#22c55e" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
