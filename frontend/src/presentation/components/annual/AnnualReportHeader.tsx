// frontend/src/presentation/components/annual/AnnualReportHeader.tsx
import type { ReactNode } from 'react'
import { Archive, CalendarRange, RefreshCw } from 'lucide-react'
import type { ReportDetail } from '@/domain/Report'
import { isRefreshableAnnualReport } from '@/presentation/config/annualReports'

export default function AnnualReportHeader({ report, actions }: { report: ReportDetail; actions?: ReactNode }) {
  const refreshable = isRefreshableAnnualReport(report.report_year ?? 0)
  return (
    <header className="flex flex-col gap-4 rounded-2xl border border-apple-divider bg-apple-surface p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><CalendarRange size={24} /></span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-apple-dark md:text-3xl">{report.report_year} 연간 보고서</h1>
            <p className="mt-2 text-sm tabular-nums text-apple-dark">{report.week_start} – {report.week_end}</p>
          </div>
        </div>
        {actions}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-apple-divider pt-3 text-[13px] text-apple-mid">
        <span className="inline-flex items-center gap-1.5 font-medium text-apple-dark">
          {refreshable ? <RefreshCw size={14} /> : <Archive size={14} />}
          {refreshable ? '집계 중 · 5분마다 자동 갱신' : '확정 보고서 · 자동 갱신 없음'}
        </span>
        <span>보고서 기준일 {report.report_date}</span>
      </div>
    </header>
  )
}
