// frontend/src/presentation/components/charts/SlaMonthlyLineChart.tsx
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { CHART_COLORS } from '@/shared/ui'
import {
  SLA_TARGET_RATE, CHART_HEIGHT, CHART_TICK_FONT_SIZE,
  CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR,
  CHART_STROKE_WIDTH, CHART_DOT_RADIUS, CHART_ACTIVE_DOT_RADIUS,
  CHART_GRADIENT_STOP_START, CHART_GRADIENT_STOP_END,
} from '@/shared/constants'

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
    <div className="bg-white border border-apple-divider rounded-lg shadow-sm px-3 py-2 text-ui-xs">
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
          <h3 className="text-ui-base font-semibold text-apple-dark">{title}</h3>
          <span className="text-ui-xs text-apple-light">{subtitle}</span>
        </div>
        <div className="flex items-center justify-center" style={{ height: CHART_HEIGHT }}>
          <p className="text-ui-sm text-apple-light">SLA 데이터가 없습니다</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-ui-base font-semibold text-apple-dark">{title}</h3>
        <span className="text-ui-xs text-apple-light">{subtitle}</span>
      </div>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={CHART_GRADIENT_STOP_START} />
              <stop offset="100%" stopColor={color} stopOpacity={CHART_GRADIENT_STOP_END} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={SLA_TARGET_RATE}
            stroke={CHART_COLORS.slaTarget}
            strokeDasharray="4 4"
            label={{ value: `목표 ${SLA_TARGET_RATE}%`, position: 'insideTopRight', fontSize: 10, fill: CHART_COLORS.axisText }}
          />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={CHART_LEGEND_ICON_SIZE}
            formatter={(value: string) => (
              <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>{value}</span>
            )}
          />
          <Area
            type="monotone"
            dataKey="rate"
            name="달성률"
            stroke={color}
            strokeWidth={CHART_STROKE_WIDTH}
            fill={`url(#${gradientId})`}
            dot={({ cx, cy, payload }: any) =>
              payload.rate !== null ? (
                <circle key={`dot-${payload.month}`} cx={cx} cy={cy} r={CHART_DOT_RADIUS} fill={color} stroke="none" />
              ) : <g key={`dot-${payload.month}`} />
            }
            activeDot={{ r: CHART_ACTIVE_DOT_RADIUS }}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
