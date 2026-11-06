// frontend/src/presentation/components/annual/AnnualMonthlyComparison.tsx
import designTokens from '@/presentation/config/designTokens.json'
import { memo, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Legend, Rectangle, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { MonthlyCountEntry } from '@/domain/Dashboard'
import { MONTHLY_COUNT_COLORS } from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import {
  buildAnnualMonthlyComparison,
  type AnnualMonthlyComparisonEntry,
} from '@/presentation/utils/annualMonthlyComparison'

interface Props {
  created: MonthlyCountEntry[]
  resolved: MonthlyCountEntry[]
  previousCreated?: MonthlyCountEntry[]
  previousResolved?: MonthlyCountEntry[]
  year: number
  periodEnd: string
  subtitle: string
  onSelectMonth?: (month: number, series: 'created' | 'resolved', count: number) => void
}

const SERIES = [
  { key: 'created', previous: 'previousCreated', name: '등록', color: MONTHLY_COUNT_COLORS.created },
  { key: 'resolved', previous: 'previousResolved', name: '해결', color: MONTHLY_COUNT_COLORS.resolved },
] as const

const formatCount = (value: number | null) => value === null ? '—' : value.toLocaleString('ko-KR')

type ComparisonRow = AnnualMonthlyComparisonEntry & { previousCreated: number | null; previousResolved: number | null }

function ForegroundBar({ x = 0, y, width = 0, height, fill }: { x?: number; y?: number; width?: number; height?: number; fill?: string }) {
  return <Rectangle x={x + width * 0.18} y={y} width={width * 0.64} height={height} fill={fill} radius={[3, 3, 0, 0]} />
}

function ComparisonTooltip({ active, payload, year, compare }: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: ComparisonRow }>
  year: number
  compare: boolean
}) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  return (
    <div className="min-w-36 rounded-xl border border-apple-divider bg-apple-surface px-4 py-3 text-label text-apple-dark shadow-apple-sm">
      <p className="mb-2 font-semibold">{year}년 {row.month}</p>
      {SERIES.map((series) => (
        <div key={series.key} className="mt-1 flex items-center justify-between gap-6">
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: series.color }} />
            {series.name}
          </span>
          <span className="font-semibold tabular-nums">{row[series.key] === null ? '데이터 없음' : `${formatCount(row[series.key])}건`}</span>
        </div>
      ))}
      {compare && <div className="mt-2 border-t border-apple-divider pt-2">
        <p className="font-medium">{year - 1}년 {row.month}</p>
        {SERIES.map((series) => <div key={series.key} className="mt-1 flex justify-between gap-6"><span>{series.name}</span><span className="tabular-nums">{row[series.previous] === null ? '데이터 없음' : `${formatCount(row[series.previous])}건`}</span></div>)}
      </div>}
    </div>
  )
}

function AnnualMonthlyComparison({ created, resolved, previousCreated = [], previousResolved = [], year, periodEnd, subtitle, onSelectMonth }: Props) {
  const exportMode = useDashboardExportMode()
  const [tableOpen, setTableOpen] = useState(false)
  const previous = new Map(buildAnnualMonthlyComparison(previousCreated, previousResolved, year - 1, `${year - 1}-12-31`).map((row) => [row.monthNumber, row]))
  const rows = buildAnnualMonthlyComparison(created, resolved, year, periodEnd).map((row) => ({
    ...row,
    previousCreated: previous.get(row.monthNumber)?.created ?? null,
    previousResolved: previous.get(row.monthNumber)?.resolved ?? null,
  }))
  const compare = rows.some((row) => row.previousCreated !== null || row.previousResolved !== null)
  const hasData = rows.some((row) => row.created !== null || row.resolved !== null)
  const hasMissing = rows.some((row) => row.created === null || row.resolved === null || (compare && (row.previousCreated === null || row.previousResolved === null)))
  const allZero = hasData && rows.every((row) => row.created === 0 && row.resolved === 0)
  const axisWidth = exportMode ? 56 : Math.ceil(designTokens.typography.chart.tick * 4)
  const chartMinWidth = exportMode ? rows.length > 8 ? 560 : 300 : Math.max(300, rows.length * 56 + axisWidth + 12)
  const exportData = exportMode ? JSON.stringify({
    headers: ['월', '등록 건수', '해결 건수', ...(compare ? [`${year - 1}년 등록 건수`, `${year - 1}년 해결 건수`] : [])],
    rows: rows.map((row) => [row.month, row.created, row.resolved, ...(compare ? [row.previousCreated, row.previousResolved] : [])]),
  }) : undefined

  return (
    <div className="card min-w-0">
      <div data-pdf-kind="chart" data-pdf-title="월별 등록 · 해결 비교" data-export-table={exportData}>
        <div className="mb-5 flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-section-title font-semibold text-apple-dark">월별 등록 · 해결 비교</h3>
          </div>
          <span className="rounded-lg bg-apple-gray px-3 py-1.5 text-caption font-medium text-apple-dark">{subtitle}</span>
        </div>
        {hasData || compare ? (
          <div className="overflow-x-auto pb-1">
            <div style={{ minWidth: chartMinWidth }}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart accessibilityLayer data={rows} margin={{ top: 12, right: 12, left: 0, bottom: 4 }} barGap={4}>
                  <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" interval={0} tick={{ fontSize: designTokens.typography.chart.tick, fill: 'rgb(var(--color-apple-dark))' }} tickMargin={10} axisLine={false} tickLine={false} height={38} />
                  {compare && <XAxis xAxisId="previous" dataKey="month" hide />}
                  <YAxis allowDecimals={false} tick={{ fontSize: designTokens.typography.chart.tick, fill: 'rgb(var(--color-apple-dark))' }} tickFormatter={(value: number) => value.toLocaleString('ko-KR')} width={axisWidth} axisLine={false} tickLine={false} />
                  <Tooltip filterNull={false} cursor={{ fill: 'rgb(var(--color-apple-gray))' }} content={<ComparisonTooltip year={year} compare={compare} />} />
                  <Legend iconSize={designTokens.chart.legendIconSize} wrapperStyle={{ paddingTop: 12 }} formatter={(value: string) => <span className="ml-1 font-medium text-apple-dark" style={{ fontSize: designTokens.typography.chart.legend }}>{value}</span>} />
                  {compare && SERIES.map((series) => (
                    <Bar key={series.previous} xAxisId="previous" dataKey={series.previous} name={`${year - 1}년 동월`}
                      legendType={series.key === 'created' ? 'square' : 'none'} fill={CHART_COLORS.previousYear} fillOpacity={0.55}
                      radius={[4, 4, 0, 0]} maxBarSize={32} isAnimationActive={false} pointerEvents="none" />
                  ))}
                  {SERIES.map((series) => (
                    <Bar key={series.key} dataKey={series.key} name={compare ? `${year}년 ${series.name}` : series.name} legendType="square" fill={series.color} shape={compare ? <ForegroundBar /> : undefined} radius={[4, 4, 0, 0]} maxBarSize={32} isAnimationActive={!exportMode}
                      cursor={onSelectMonth && !exportMode ? 'pointer' : undefined}
                      onClick={onSelectMonth && !exportMode ? (entry) => {
                        const row = entry.payload as AnnualMonthlyComparisonEntry
                        const count = row?.[series.key]
                        if (count != null) onSelectMonth(row.monthNumber, series.key, count)
                      } : undefined}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <p className="flex min-h-44 items-center justify-center text-label text-apple-dark">해당 기간의 월별 데이터가 없습니다.</p>
        )}
        {allZero && <p className="mt-2 text-label text-apple-dark">해당 기간의 등록·해결 건수가 모두 0건입니다.</p>}
      </div>
      {rows.length > 0 && (
        <details open={exportMode || tableOpen} onToggle={(event) => { if (!exportMode) setTableOpen(event.currentTarget.open) }} className="group mt-5 border-t border-apple-divider pt-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg py-1 text-label font-semibold text-apple-dark outline-none focus-visible:ring-2 focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden">
            월별 상세 수치
            <span className="flex items-center gap-2 text-caption font-medium">단위: 건<ChevronDown size={16} className="transition-transform group-open:rotate-180" /></span>
          </summary>
          <div data-pdf-kind="table" data-pdf-title={`${year}년 월별 등록 · 해결 건수`} className="mt-3 overflow-x-auto rounded-xl border border-apple-divider">
            <table className="w-full min-w-[360px] table-fixed text-body text-apple-dark">
              <caption className="sr-only">{subtitle} 월별 등록 및 해결 건수</caption>
              <thead className="bg-apple-gray">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left font-semibold">월</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SERIES[0].color }} />등록</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SERIES[1].color }} />해결</th>
                  {compare && SERIES.map((series) => <th key={series.key} scope="col" className="px-4 py-3 text-right font-semibold">{year - 1}년 {series.name}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-divider">
                {rows.map((row) => (
                  <tr key={row.monthNumber} className="even:bg-apple-gray/40">
                    <th scope="row" className="px-4 py-2.5 text-left font-medium">{row.month}</th>
                    {SERIES.map((series) => (
                      <td key={series.key} className="px-4 py-2.5 text-right font-semibold tabular-nums" aria-label={row[series.key] === null ? `${series.name} 데이터 없음` : undefined}>
                        {onSelectMonth && !exportMode && row[series.key] !== null ? (
                          <button type="button" aria-label={`${row.month} ${series.name} ${formatCount(row[series.key])}건 상세 보기`} onClick={() => onSelectMonth(row.monthNumber, series.key, row[series.key]!)} className="rounded px-2 py-1 text-brand-600 underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">{formatCount(row[series.key])}</button>
                        ) : formatCount(row[series.key])}
                      </td>
                    ))}
                    {compare && SERIES.map((series) => <td key={series.key} className="px-4 py-2.5 text-right tabular-nums">{formatCount(row[series.previous])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {hasMissing && <p className="mt-2 text-caption text-apple-dark">—는 월별 데이터가 없는 항목입니다.</p>}
        </details>
      )}
    </div>
  )
}

export default memo(AnnualMonthlyComparison)
