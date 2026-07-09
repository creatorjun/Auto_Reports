// frontend/src/presentation/components/charts/SlaMonthlyLineChart.tsx
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'

export interface MonthlyEntry {
  month: string
  year: number
  month_num: number
  rate: number
  met: number
  total: number
}

interface Props {
  title: string
  subtitle: string
  monthly: MonthlyEntry[]
  color: string
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const p = payload[0]
  const meta: MonthlyEntry | undefined = p?.payload?.meta
  return (
    <div className="bg-white border border-apple-divider rounded-lg shadow-sm px-3 py-2 text-[11px]">
      <p className="font-semibold text-apple-dark mb-1">{label}</p>
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
        <span className="text-apple-light">달성률:</span>
        <span className="font-medium tabular-nums" style={{ color: p.color }}>
          {p.value !== null ? `${p.value}%` : '-'}
        </span>
        {meta && meta.total > 0 && (
          <span className="text-apple-light/70">({meta.met}/{meta.total}건)</span>
        )}
      </div>
    </div>
  )
}

export default function SlaMonthlyLineChart({ title, subtitle, monthly, color }: Props) {
  const gradientId = `sla-grad-${color.replace('#', '')}`

  const chartData = monthly.map((e) => ({
    month: e.month,
    rate: e.total > 0 ? e.rate : null,
    meta: e,
  }))

  const hasData = chartData.some((d) => d.rate !== null)

  if (!hasData) {
    return (
      <div className="card flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-apple-dark">{title}</h3>
          <span className="text-[11px] text-apple-light">{subtitle}</span>
        </div>
        <div className="flex items-center justify-center h-[240px]">
          <p className="text-[12px] text-apple-light">SLA 데이터가 없습니다</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-apple-dark">{title}</h3>
        <span className="text-[11px] text-apple-light">{subtitle}</span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 11, fill: '#8e8e93' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11, fill: '#8e8e93' }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={80}
            stroke="#e5e7eb"
            strokeDasharray="4 4"
            label={{ value: '목표 80%', position: 'insideTopRight', fontSize: 10, fill: '#9ca3af' }}
          />
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
          <Area
            type="monotone"
            dataKey="rate"
            name="달성률"
            stroke={color}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={({ cx, cy, payload }: any) =>
              payload.rate !== null ? (
                <circle key={`dot-${payload.month}`} cx={cx} cy={cy} r={4} fill={color} stroke="none" />
              ) : <g key={`dot-${payload.month}`} />
            }
            activeDot={{ r: 6 }}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
