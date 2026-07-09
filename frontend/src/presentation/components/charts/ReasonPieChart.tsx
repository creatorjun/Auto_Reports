// frontend/src/presentation/components/charts/ReasonPieChart.tsx
import { memo } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { TooltipProps } from 'recharts'
import type { ValueType, NameType } from 'recharts/types/component/DefaultTooltipContent'
import { PIE_COLORS, CHART_HEIGHT, CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR } from '@/shared/constants'

const REASON_COLORS = [...PIE_COLORS, '#10b981', '#f97316'] as const

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
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${Math.round(percent * 100)}%`}
    </text>
  )
}

function CustomTooltip({ active, payload }: TooltipProps<ValueType, NameType>) {
  if (!active || !payload?.length) return null
  const name  = payload[0].name  as string
  const value = payload[0].value as number
  return (
    <div className="bg-white border border-apple-divider/60 rounded-xl shadow-apple px-3 py-2 text-[12px]">
      <p className="font-medium text-apple-dark">{name}</p>
      <p className="text-apple-light">{value}건</p>
    </div>
  )
}

function ReasonPieChart({ byStatus }: { byStatus: Record<string, number> }) {
  const data = Object.entries(byStatus)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  if (!data.length) return null

  return (
    <div className="card flex flex-col">
      <h3 className="text-sm font-semibold text-apple-dark mb-3">🥧 SLA 지연 사유</h3>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            outerRadius={125}
            dataKey="value"
            labelLine={false}
            label={CustomLabel}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={REASON_COLORS[i % REASON_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={(props) => <CustomTooltip {...props} />} />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={CHART_LEGEND_ICON_SIZE}
            formatter={(value: string) => (
              <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>
                {value.length > 10 ? value.slice(0, 10) + '…' : value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(ReasonPieChart)
