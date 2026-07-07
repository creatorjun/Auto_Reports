// frontend/src/presentation/components/charts/SlaMonthlyLineChart.tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'

interface MonthlyEntry {
  month: string
  year: number
  month_num: number
  rate: number
  met: number
  total: number
}

interface SlaMonthlyBreakdown {
  monthly?: MonthlyEntry[]
  error?: string
}

interface Props {
  w15Breakdown: SlaMonthlyBreakdown
  w16Breakdown: SlaMonthlyBreakdown
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-apple-divider rounded-lg shadow-sm px-3 py-2 text-[11px]">
      <p className="font-semibold text-apple-dark mb-1">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
          <span className="text-apple-light">{p.name}:</span>
          <span className="font-medium tabular-nums" style={{ color: p.color }}>
            {p.value !== null ? `${p.value}%` : '-'}
          </span>
          {p.payload[`${p.dataKey}_meta`] && (
            <span className="text-apple-light/70">
              ({p.payload[`${p.dataKey}_meta`].met}/{p.payload[`${p.dataKey}_meta`].total})
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

export default function SlaMonthlyLineChart({ w15Breakdown, w16Breakdown }: Props) {
  const w15List = w15Breakdown.monthly ?? []
  const w16List = w16Breakdown.monthly ?? []

  const allMonths: string[] = []
  const seen = new Set<string>()
  ;[...w15List, ...w16List].forEach((e) => {
    if (!seen.has(e.month)) { seen.add(e.month); allMonths.push(e.month) }
  })

  const w15Map = Object.fromEntries(w15List.map((e) => [e.month, e]))
  const w16Map = Object.fromEntries(w16List.map((e) => [e.month, e]))

  const chartData = allMonths.map((month) => ({
    month,
    '초기대응': w15Map[month]?.total ? w15Map[month].rate : null,
    '초기대응_meta': w15Map[month] ?? null,
    '해결시간': w16Map[month]?.total ? w16Map[month].rate : null,
    '해결시간_meta': w16Map[month] ?? null,
  }))

  const hasData = chartData.some((d) => d['초기대응'] !== null || d['해결시간'] !== null)

  if (!hasData) {
    return (
      <div className="card flex items-center justify-center h-[220px]">
        <p className="text-[12px] text-apple-light">SLA 데이터가 없습니다</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-apple-dark">📈 월별 SLA 달성률</h3>
        <span className="text-[11px] text-apple-light">최근 6개월 · Jira SLA 기준</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
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
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          />
          <ReferenceLine y={80} stroke="#e5e7eb" strokeDasharray="4 4" label={{ value: '목표 80%', position: 'insideTopRight', fontSize: 10, fill: '#9ca3af' }} />
          <Line
            type="monotone"
            dataKey="초기대응"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#3b82f6', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="해결시간"
            stroke="#22c55e"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#22c55e', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
