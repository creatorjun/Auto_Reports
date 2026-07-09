// frontend/src/presentation/components/charts/MonthlyCountChart.tsx
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { CHART_COLORS } from '@/shared/ui'
import {
  CHART_HEIGHT, CHART_TICK_FONT_SIZE,
  CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR,
  CHART_STROKE_WIDTH, CHART_DOT_RADIUS, CHART_ACTIVE_DOT_RADIUS,
  CHART_GRADIENT_STOP_START, CHART_GRADIENT_STOP_END,
} from '@/shared/constants'

export interface MonthlyCountEntry {
  month: string
  year: number
  month_num: number
  count: number
}

interface Props {
  title: string
  subtitle: string
  monthly: MonthlyCountEntry[]
  color: string
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div className="bg-white border border-apple-divider rounded-lg shadow-sm px-3 py-2 text-ui-xs">
      <p className="font-semibold text-apple-dark mb-1">{label}</p>
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
        <span className="text-apple-light">건수:</span>
        <span className="font-medium tabular-nums" style={{ color: p.color }}>{p.value}건</span>
      </div>
    </div>
  )
}

export default function MonthlyCountChart({ title, subtitle, monthly, color }: Props) {
  const gradientId = `mc-grad-${color.replace('#', '')}`
  const chartData = monthly.map((e) => ({ month: e.month, count: e.count }))
  const hasData = chartData.some((d) => d.count > 0)

  if (!hasData) {
    return (
      <div className="card flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-ui-base font-semibold text-apple-dark">{title}</h3>
          <span className="text-ui-xs text-apple-light">{subtitle}</span>
        </div>
        <div className="flex items-center justify-center" style={{ height: CHART_HEIGHT }}>
          <p className="text-ui-sm text-apple-light">데이터가 없습니다</p>
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
            allowDecimals={false}
            tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
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
            dataKey="count"
            name="건수"
            stroke={color}
            strokeWidth={CHART_STROKE_WIDTH}
            fill={`url(#${gradientId})`}
            dot={({ cx, cy }: any) => (
              <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={CHART_DOT_RADIUS} fill={color} stroke="none" />
            )}
            activeDot={{ r: CHART_ACTIVE_DOT_RADIUS }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
