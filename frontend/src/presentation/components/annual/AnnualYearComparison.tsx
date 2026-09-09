// frontend/src/presentation/components/annual/AnnualYearComparison.tsx
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import type { ReportDetail } from '@/domain/Report'
import { WIDGET_ID } from '@/domain/WidgetId'
import { RequestError } from '@/application/errors/RequestError'
import { useAnnualReport } from '@/presentation/hooks/useReport'
import { buildDashboardData } from '@/presentation/hooks/useDashboardData'
import { ANNUAL_REPORT_YEARS, isRefreshableAnnualReport } from '@/presentation/config/annualReports'

export default function AnnualYearComparison({ report }: { report: ReportDetail }) {
  const query2024 = useAnnualReport(2024)
  const query2025 = useAnnualReport(2025)
  const query2026 = useAnnualReport(2026)
  const queries = [query2024, query2025, query2026]
  const summaries = useMemo(() => [query2024.data, query2025.data, query2026.data].map((cached, index) => {
    const data = ANNUAL_REPORT_YEARS[index] === report.report_year ? report : cached
    return { data, totals: data ? buildDashboardData(data).yearly : null }
  }), [report, query2024.data, query2025.data, query2026.data])
  const columns = ANNUAL_REPORT_YEARS.map((year, index) => {
    const query = queries[index]
    const { data, totals } = summaries[index]
    const unavailable = query.error instanceof RequestError && query.error.status === 404
    return {
      year, data, query,
      created: data?.widgets[WIDGET_ID.YEARLY_CREATED] ? totals!.w1YearlyCreated : null,
      resolved: data?.widgets[WIDGET_ID.YEARLY_RESOLVED] ? totals!.w2YearlyResolved : null,
      state: query.isLoading ? '불러오는 중' : unavailable ? '보고서 없음' : '조회 실패',
    }
  })
  const largest = Math.max(1, ...columns.flatMap((column) => [column.created ?? 0, column.resolved ?? 0]))

  return (
    <section aria-labelledby="annual-comparison-title" className="overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface">
      <div className="flex flex-wrap items-end justify-between gap-2 px-4 pb-4 pt-5 md:px-6">
        <div>
          <h2 id="annual-comparison-title" className="text-lg font-semibold text-apple-dark">3개년 실적 비교</h2>
          <p className="mt-1 text-[13px] text-apple-mid">전체 요청 유형 · 각 보고서의 연간 누적 기준</p>
        </div>
        <span className="text-[12px] text-apple-mid">연도를 선택하면 상세 보고서로 이동합니다.</span>
      </div>
      <table className="w-full table-fixed border-collapse text-sm text-apple-dark">
        <caption className="sr-only">2024년부터 2026년까지 연간 생성 및 해결 건수. 2026년은 집계 기간까지의 누적 실적입니다.</caption>
        <thead>
          <tr className="border-y border-apple-divider bg-apple-gray/60">
            <th scope="col" className="w-[25%] px-3 py-3 text-left font-medium md:px-6">구분</th>
            {columns.map(({ year, data }) => (
              <th key={year} scope="col" className={`px-2 py-3 text-center ${year === report.report_year ? 'bg-brand-50' : ''}`}>
                <Link to={`/reports/annual/${year}`} aria-current={year === report.report_year ? 'page' : undefined} className="inline-flex items-center gap-1 rounded-md text-base font-semibold text-apple-dark hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 md:text-xl">
                  {year}<ArrowUpRight size={14} className="hidden sm:block" />
                </Link>
                <span className="mt-1 block text-[11px] font-medium text-apple-mid sm:text-[12px]">{isRefreshableAnnualReport(year) ? '집계 중' : '연간 확정'}</span>
                <span className="mt-1 block text-[11px] font-normal tabular-nums text-apple-mid sm:text-[12px]">{data ? `${data.week_start.slice(5).replace('-', '.')}–${data.week_end.slice(5).replace('-', '.')}` : '기간 미확인'}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {([{ key: 'created', label: '생성', color: 'rgb(var(--color-chart-created))' }, { key: 'resolved', label: '해결', color: 'rgb(var(--color-chart-resolved))' }] as const).map((metric) => (
            <tr key={metric.key} className="border-b border-apple-divider last:border-0">
              <th scope="row" className="px-3 py-4 text-left font-semibold md:px-6">{metric.label}<span className="ml-1 text-[12px] font-normal text-apple-mid">(건)</span></th>
              {columns.map((column) => {
                const value = column[metric.key]
                return (
                  <td key={column.year} className={`px-2 py-4 text-center md:px-6 ${column.year === report.report_year ? 'bg-brand-50/50' : ''}`}>
                    <span className="block text-lg font-semibold tabular-nums tracking-tight sm:text-2xl">{value === null ? '—' : value.toLocaleString('ko-KR')}</span>
                    {value === null ? (
                      <span className="mt-1 block text-[11px] text-apple-mid">{column.data ? '집계 없음' : column.state}</span>
                    ) : (
                      <div aria-hidden="true" className="mx-auto mt-2 h-1.5 max-w-48 overflow-hidden rounded-full bg-apple-divider/60"><div className="h-full rounded-full" style={{ width: `${value / largest * 100}%`, backgroundColor: metric.color }} /></div>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="space-y-2 border-t border-apple-divider px-4 py-3 text-[12px] leading-5 text-apple-mid md:px-6">
        <p>2026년은 표시된 기간까지의 누적 실적입니다. 과년도 전체 실적과 집계 기간이 다르며, 아래 상세 필터는 이 비교표에 적용되지 않습니다.</p>
        {columns.filter(({ query, year }) => query.isError && year !== report.report_year).map(({ year, query, data }) => (
          <p key={year} className="flex flex-wrap items-center gap-2">
            {year}년 {data ? '갱신에 실패하여 이전 조회 값을 표시합니다.' : '보고서를 불러오지 못했습니다.'}
            <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()} className="rounded px-1 font-semibold text-brand-600 underline underline-offset-2 disabled:opacity-50">다시 조회</button>
          </p>
        ))}
      </div>
    </section>
  )
}
