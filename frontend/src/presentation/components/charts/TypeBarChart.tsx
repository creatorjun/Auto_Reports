// frontend/src/presentation/components/charts/TypeBarChart.tsx
import { memo, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { PIE_COLORS, CHART_HEIGHT, CHART_TICK_FONT_SIZE, CHART_LEGEND_ICON_SIZE, CHART_LEGEND_COLOR } from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

interface Props {
  byType: Record<string, ResolutionTypeEntry>
  onTypeClick?: (issueType: string) => void
}

function TypeBarChart({ byType, onTypeClick }: Props) {
  const exportMode = useDashboardExportMode()
  const [chartWidth, setChartWidth] = useState(0)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const interactive = !exportMode && Boolean(onTypeClick)
  const data = Object.entries(byType).map(([name, d]) => ({ name, avg_days: d.avg_days, avg_hours: d.avg_hours, count: d.count }))
  if (!data.length) return null
  const exportTickLimit = Math.max(2, Math.floor(((chartWidth - 80) / data.length - 12) / 14))
  const formatExportTick = (value: string) => {
    const characters = Array.from(value)
    return characters.length > exportTickLimit
      ? `${characters.slice(0, exportTickLimit - 1).join('')}…`
      : value
  }
  return (
    <div data-pdf-kind="chart" className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⏱️ 유형별 평균 처리일</h3>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT} onResize={exportMode ? (width) => setChartWidth(width) : undefined}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="name" tick={{ fontSize: CHART_TICK_FONT_SIZE }} tickFormatter={exportMode ? formatExportTick : undefined} />
          <YAxis tick={{ fontSize: CHART_TICK_FONT_SIZE }} unit="일" />
          <Tooltip formatter={(v) => [`${v}일`]} />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={CHART_LEGEND_ICON_SIZE}
            payload={data.map((d, i) => ({ value: d.name, type: 'circle', color: PIE_COLORS[i % PIE_COLORS.length] }))}
            formatter={(value: string) => (
              <span style={{ fontSize: CHART_LEGEND_ICON_SIZE + 4, color: CHART_LEGEND_COLOR }}>
                {!exportMode && value.length > 10 ? value.slice(0, 10) + '…' : value}
              </span>
            )}
          />
          <Bar isAnimationActive={!exportMode} dataKey="avg_days" radius={[6, 6, 0, 0]}
            style={interactive ? { cursor: 'pointer' } : undefined}
            onClick={interactive ? (entry: { payload?: { name?: string }; name?: string }) => {
              const issueType = entry?.payload?.name ?? entry?.name
              if (issueType && data.some((row) => row.name === issueType)) onTypeClick?.(issueType)
            } : undefined}
          >
            {data.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {interactive && (
        <details open={detailsOpen} onToggle={(event) => setDetailsOpen(event.currentTarget.open)} className="group mt-4 border-t border-apple-divider pt-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg py-2 text-base font-semibold text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden">
            건수 상세 보기<ChevronDown size={16} className="shrink-0 transition-transform group-open:rotate-180" />
          </summary>
          <div data-pdf-kind="table" className="mt-2 overflow-x-auto rounded-xl border border-apple-divider">
            <table className="w-full min-w-[520px] text-sm text-apple-dark">
              <caption className="sr-only">요청 유형별 처리 대상 건수와 평균 처리 기간</caption>
              <thead className="bg-apple-gray">
                <tr>
                  <th scope="col" className="px-3 py-3 text-left font-semibold">유형</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">처리 대상</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">평균 일</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">평균 시간</th>
                  <th scope="col" className="px-3 py-3 text-center font-semibold">상세</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-divider">
                {data.map((entry) => (
                  <tr key={entry.name}>
                    <th scope="row" className="px-3 py-2 text-left font-medium">{entry.name}</th>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums">{entry.count.toLocaleString('ko-KR')}건</td>
                    <td className="px-3 py-2 text-right tabular-nums">{entry.avg_days.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{entry.avg_hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2 text-center">
                      <button type="button" onClick={() => onTypeClick?.(entry.name)} aria-label={`${entry.name} 처리 대상 ${entry.count.toLocaleString('ko-KR')}건 상세 보기`} className="min-h-10 whitespace-nowrap rounded-lg px-3 py-1 font-semibold text-brand-600 underline underline-offset-4 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">상세 보기</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  )
}

export default memo(TypeBarChart)
