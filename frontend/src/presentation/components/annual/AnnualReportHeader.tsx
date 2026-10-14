// frontend/src/presentation/components/annual/AnnualReportHeader.tsx
import type { ReactNode } from 'react'
import { CalendarRange } from 'lucide-react'
import type { ReportDetail } from '@/domain/Report'

export default function AnnualReportHeader({ report, actions }: { report: ReportDetail; actions?: ReactNode }) {
  return (
    <header className="flex flex-col gap-4 rounded-2xl border border-apple-divider bg-apple-surface p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><CalendarRange size={24} /></span>
          <div>
            <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">{report.report_year} 연간 보고서</h1>
            <p className="mt-2 text-label tabular-nums text-apple-dark">{report.week_start} – {report.week_end}</p>
          </div>
        </div>
        {actions}
      </div>
    </header>
  )
}
