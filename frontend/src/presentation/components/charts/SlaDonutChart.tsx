// frontend/src/presentation/components/charts/SlaDonutChart.tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#22c55e', '#ef4444']

export default function SlaDonutChart({ met, violated }: { met: number; violated: number }) {
  const data = [
    { name: 'SLA 만족', value: met },
    { name: 'SLA 위반', value: violated }
  ]
  const total = met + violated
  const rate = total > 0 ? Math.round((met / total) * 100) : 0
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">🎯 SLA 만족 vs 위반</h3>
      <div className="relative">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={data} cx="50%" cy="45%" innerRadius={60} outerRadius={90} dataKey="value">
              {data.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
            </Pie>
            <Tooltip formatter={(v) => [`${v}건`]} />
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
            <p className="text-2xl font-bold text-gray-800">{rate}%</p>
            <p className="text-xs text-gray-400">만족률</p>
          </div>
        </div>
      </div>
    </div>
  )
}
