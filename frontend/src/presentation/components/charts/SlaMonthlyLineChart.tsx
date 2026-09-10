// frontend/src/presentation/components/charts/SlaMonthlyLineChart.tsx
import { memo, useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { CHART_COLORS } from '@/presentation/config/ui'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import {
  SLA_TARGET_RATE, CHART_HEIGHT, CHART_TICK_FONT_SIZE,
  CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR,
  CHART_STROKE_WIDTH, CHART_DOT_RADIUS, CHART_ACTIVE_DOT_RADIUS,
  CHART_GRADIENT_STOP_START, CHART_GRADIENT_STOP_END,
} from '@/presentation/config/constants'
import type { MonthlyEntry } from '@/domain/Dashboard'

interface Props {
  title: string
  subtitle: string
  monthly: MonthlyEntry[]
  color: string
  onMonthClick?: (entry: MonthlyEntry, status: 'all' | 'met' | 'violated') => void
}

interface ChartPoint {
  month: string
  rate: number | null
  meta: MonthlyEntry
}

interface ChartDotProps {
  cx?: number
  cy?: number
  payload?: ChartPoint
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const p    = payload[0]
  const meta: MonthlyEntry | undefined = p?.payload?.meta
  return (
    <div className="bg-apple-surface border border-apple-divider rounded-lg shadow-sm px-3 py-2 text-ui-xs">
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

function SlaMonthlyLineChart({ title, subtitle, monthly, color, onMonthClick }: Props) {
  const exportMode = useDashboardExportMode()
  const [detailsOpen, setDetailsOpen] = useState(false)
  const gradientId = `sla-grad-${useId().replace(/:/g, '')}`
  const interactive = !exportMode && Boolean(onMonthClick)
  const chartData  = monthly.map((e) => ({
    month: e.month,
    rate:  e.total > 0 ? e.rate : null,
    meta:  e,
  }))
  const hasData = chartData.some((d) => d.rate !== null)
  const renderDot = ({ cx, cy, payload }: ChartDotProps, active = false) => {
    if (!payload || payload.rate === null) return <g key={`dot-${payload?.month ?? 'empty'}`} />
    return (
      <circle
        key={`dot-${payload.month}`}
        cx={cx} cy={cy} r={active ? CHART_ACTIVE_DOT_RADIUS : CHART_DOT_RADIUS}
        fill={color} stroke="none"
        style={interactive ? { cursor: 'pointer' } : undefined}
        onClick={interactive ? (event) => {
          event.stopPropagation()
          onMonthClick?.(payload.meta, 'all')
        } : undefined}
      />
    )
  }
  const detailTable = interactive && monthly.length > 0 && (
    <details open={detailsOpen} onToggle={(event) => setDetailsOpen(event.currentTarget.open)} className="group mt-4 border-t border-apple-divider pt-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg py-2 text-base font-semibold text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden">
        건수 상세 보기<ChevronDown size={16} className="shrink-0 transition-transform group-open:rotate-180" />
      </summary>
      <div data-pdf-kind="table" className="mt-2 overflow-x-auto rounded-xl border border-apple-divider">
        <table className="w-full min-w-[320px] text-sm text-apple-dark">
          <caption className="sr-only">{title} 월별 대상, 준수 및 위반 건수</caption>
          <thead className="bg-apple-gray">
            <tr>
              <th scope="col" className="px-3 py-3 text-left font-semibold">월</th>
              <th scope="col" className="px-2 py-3 text-right font-semibold">대상</th>
              <th scope="col" className="px-2 py-3 text-right font-semibold">준수</th>
              <th scope="col" className="px-2 py-3 text-right font-semibold">위반</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider">
            {monthly.map((entry) => (
              <tr key={`${entry.year}-${entry.month_num}`}>
                <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-medium">{entry.month_num}월</th>
                {([
                  { status: 'all', label: '대상', count: entry.total },
                  { status: 'met', label: '준수', count: entry.met },
                  { status: 'violated', label: '위반', count: Math.max(0, entry.total - entry.met) },
                ] as const).map(({ status, label, count }) => (
                  <td key={status} className="px-2 py-2 text-right tabular-nums">
                    <button type="button" onClick={() => onMonthClick?.(entry, status)} aria-label={`${title} ${entry.year}년 ${entry.month_num}월 ${label} ${count.toLocaleString('ko-KR')}건 상세 보기`} className="min-h-10 min-w-10 rounded-lg px-2 py-1 font-semibold text-brand-600 underline underline-offset-4 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
                      {count.toLocaleString('ko-KR')}
                    </button>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )

  if (!hasData) {
    return (
      <div data-pdf-kind="chart" className="card flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-ui-base font-semibold text-apple-dark">{title}</h3>
          <span className="text-ui-xs text-apple-light">{subtitle}</span>
        </div>
        <div className="flex items-center justify-center" style={{ height: CHART_HEIGHT }}>
          <p className="text-ui-sm text-apple-light">SLA 데이터가 없습니다</p>
        </div>
        {detailTable}
      </div>
    )
  }

  return (
    <div data-pdf-kind="chart" className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-ui-base font-semibold text-apple-dark">{title}</h3>
        <span className="text-ui-xs text-apple-light">{subtitle}</span>
      </div>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
          style={interactive ? { cursor: 'pointer' } : undefined}
          onClick={interactive ? (state) => {
            const entry: MonthlyEntry | undefined = state?.activePayload?.[0]?.payload?.meta
            if (entry) onMonthClick?.(entry, 'all')
          } : undefined}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={CHART_GRADIENT_STOP_START} />
              <stop offset="100%" stopColor={color} stopOpacity={CHART_GRADIENT_STOP_END} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} width={40} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={SLA_TARGET_RATE}
            stroke={CHART_COLORS.slaTarget}
            strokeDasharray="4 4"
            label={{ value: `목표 ${SLA_TARGET_RATE}%`, position: 'insideTopRight', fontSize: 10, fill: CHART_COLORS.axisText }}
          />
          <Legend
            layout="horizontal" verticalAlign="bottom" align="center"
            iconType="circle" iconSize={CHART_LEGEND_ICON_SIZE}
            formatter={(value: string) => (
              <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>{value}</span>
            )}
          />
          <Area
            isAnimationActive={!exportMode}
            type="monotone" dataKey="rate" name="달성률"
            stroke={color} strokeWidth={CHART_STROKE_WIDTH}
            fill={`url(#${gradientId})`}
            dot={(props: ChartDotProps) => renderDot(props)}
            activeDot={interactive ? (props: ChartDotProps) => renderDot(props, true) : { r: CHART_ACTIVE_DOT_RADIUS }}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
      {detailTable}
    </div>
  )
}

export default memo(SlaMonthlyLineChart)
