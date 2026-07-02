import {
  PieChart, Pie, Cell, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'

const COLORS = ['#3b82f6','#f59e0b','#ef4444','#8b5cf6','#10b981','#f97316']

const RADIAN = Math.PI / 180

function CustomLabel({
  cx, cy, midAngle, innerRadius, outerRadius, percent
}: {
  cx: number; cy: number; midAngle: number
  innerRadius: number; outerRadius: number; percent: number
}) {
  if (percent < 0.05) return null
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text
      x={x} y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
    >
      {`${Math.round(percent * 100)}%`}
    </text>
  )
}

interface TooltipPayload {
  name: string
  value: number
  payload: { name: string; value: number }
}

function CustomTooltip({ active, payload, total }: {
  active?: boolean
  payload?: TooltipPayload[]
  total: number
}) {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="bg-white border border-apple-divider/60 rounded-xl shadow-apple px-3 py-2 text-[12px]">
      <p className="font-medium text-apple-dark">{name}</p>
      <p className="text-apple-light">{value}건 <span className="text-apple-mid font-semibold">{pct}%</span></p>
    </div>
  )
}

export default function ReasonPieChart({ breakdown }: { breakdown: Record<string, number> }) {
  const data = Object.entries(breakdown)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  if (!data.length) return null

  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="card flex flex-col">
      <h3 className="text-sm font-semibold text-apple-dark mb-3">🥧 SLA 지연 사유</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            outerRadius={85}
            dataKey="value"
            labelLine={false}
            label={CustomLabel}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={(props) => <CustomTooltip {...props} total={total} />} />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={7}
            formatter={(value: string) => (
              <span style={{ fontSize: 11, color: '#86868b' }}>
                {value.length > 10 ? value.slice(0, 10) + '…' : value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
