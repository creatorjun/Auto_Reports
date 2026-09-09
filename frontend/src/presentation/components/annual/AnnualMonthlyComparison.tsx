// frontend/src/presentation/components/annual/AnnualMonthlyComparison.tsx
import { memo, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { MonthlyCountEntry } from '@/domain/Dashboard'
import { CHART_COLORS } from '@/presentation/config/ui'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import {
  buildAnnualMonthlyComparison,
  type AnnualMonthlyComparisonEntry,
} from '@/presentation/utils/annualMonthlyComparison'

interface Props {
  created: MonthlyCountEntry[]
  resolved: MonthlyCountEntry[]
  year: number
  periodEnd: string
  subtitle: string
}

const SERIES = [
  { key: 'created', name: '등록', color: 'rgb(var(--color-chart-created))' },
  { key: 'resolved', name: '해결', color: 'rgb(var(--color-chart-resolved))' },
] as const

const formatCount = (value: number | null) => value === null ? '—' : value.toLocaleString('ko-KR')

function ComparisonTooltip({ active, payload }: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: AnnualMonthlyComparisonEntry }>
}) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  return (
    <div className="min-w-36 rounded-xl border border-apple-divider bg-apple-surface px-4 py-3 text-ui-sm text-apple-dark shadow-apple-sm">
      <p className="mb-2 font-semibold">{row.month}</p>
      {SERIES.map((series) => (
        <div key={series.key} className="mt-1 flex items-center justify-between gap-6">
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: series.color }} />
            {series.name}
          </span>
          <span className="font-semibold tabular-nums">{row[series.key] === null ? '데이터 없음' : `${formatCount(row[series.key])}건`}</span>
        </div>
      ))}
    </div>
  )
}

function AnnualMonthlyComparison({ created, resolved, year, periodEnd, subtitle }: Props) {
  const exportMode = useDashboardExportMode()
  const [tableOpen, setTableOpen] = useState(false)
  const rows = buildAnnualMonthlyComparison(created, resolved, year, periodEnd)
  const hasData = rows.some((row) => row.created !== null || row.resolved !== null)
  const hasMissing = rows.some((row) => row.created === null || row.resolved === null)
  const allZero = hasData && rows.every((row) => row.created === 0 && row.resolved === 0)

  return (
    <div className="card min-w-0">
      <div data-pdf-kind="chart" data-pdf-title="월별 등록 · 해결 비교">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-ui-base font-semibold text-apple-dark">월별 등록 · 해결 비교</h3>
            <p className="mt-1 text-ui-sm text-apple-dark">같은 월의 등록과 해결 건수를 나란히 비교합니다.</p>
          </div>
          <span className="rounded-lg bg-apple-gray px-3 py-1.5 text-ui-xs font-medium text-apple-dark">{subtitle}</span>
        </div>
        {hasData ? (
          <div className="overflow-x-auto pb-1">
            <div className={rows.length > 8 ? 'min-w-[560px]' : 'min-w-[300px]'}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart accessibilityLayer data={rows} margin={{ top: 12, right: 12, left: 0, bottom: 4 }} barGap={4}>
                  <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" interval={0} tick={{ fontSize: 12, fill: 'rgb(var(--color-apple-dark))' }} tickMargin={10} axisLine={false} tickLine={false} height={38} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: 'rgb(var(--color-apple-dark))' }} tickFormatter={(value: number) => value.toLocaleString('ko-KR')} width={56} axisLine={false} tickLine={false} />
                  <Tooltip filterNull={false} cursor={{ fill: 'rgb(var(--color-apple-gray))' }} content={<ComparisonTooltip />} />
                  <Legend iconType="square" iconSize={10} wrapperStyle={{ paddingTop: 12 }} formatter={(value: string) => <span className="ml-1 text-ui-sm font-medium text-apple-dark">{value}</span>} />
                  {SERIES.map((series) => (
                    <Bar key={series.key} dataKey={series.key} name={series.name} fill={series.color} radius={[4, 4, 0, 0]} maxBarSize={32} isAnimationActive={!exportMode} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <p className="flex min-h-44 items-center justify-center text-ui-sm text-apple-dark">해당 기간의 월별 데이터가 없습니다.</p>
        )}
        {allZero && <p className="mt-2 text-ui-sm text-apple-dark">해당 기간의 등록·해결 건수가 모두 0건입니다.</p>}
      </div>
      {rows.length > 0 && (
        <details open={exportMode || tableOpen} onToggle={(event) => { if (!exportMode) setTableOpen(event.currentTarget.open) }} className="group mt-5 border-t border-apple-divider pt-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg py-1 text-ui-sm font-semibold text-apple-dark outline-none focus-visible:ring-2 focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden">
            월별 상세 수치
            <span className="flex items-center gap-2 text-ui-xs font-medium">단위: 건<ChevronDown size={16} className="transition-transform group-open:rotate-180" /></span>
          </summary>
          <div data-pdf-kind="table" data-pdf-title={`${year}년 월별 등록 · 해결 건수`} className="mt-3 overflow-hidden rounded-xl border border-apple-divider">
            <table className="w-full table-fixed text-ui-sm text-apple-dark">
              <caption className="sr-only">{subtitle} 월별 등록 및 해결 건수</caption>
              <thead className="bg-apple-gray">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left font-semibold">월</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SERIES[0].color }} />등록</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SERIES[1].color }} />해결</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-divider">
                {rows.map((row) => (
                  <tr key={row.monthNumber} className="even:bg-apple-gray/40">
                    <th scope="row" className="px-4 py-2.5 text-left font-medium">{row.month}</th>
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums" aria-label={row.created === null ? '등록 데이터 없음' : undefined}>{formatCount(row.created)}</td>
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums" aria-label={row.resolved === null ? '해결 데이터 없음' : undefined}>{formatCount(row.resolved)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {hasMissing && <p className="mt-2 text-ui-xs text-apple-dark">—는 월별 데이터가 없는 항목입니다.</p>}
        </details>
      )}
    </div>
  )
}

export default memo(AnnualMonthlyComparison)
