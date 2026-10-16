// frontend/src/presentation/components/common/DashboardGenerateForm.tsx
import { useState, type FormEvent } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import type { ReportPeriod } from '@/domain/ReportPeriod'
import type { ReportDetail } from '@/domain/Report'
import { REPORT_PERIOD_LABELS, dashboardReportDateRange, reportToday } from '@/application/services/reportPeriod'
import { useReportGeneration } from '@/presentation/context/ReportGenerationContext'

export default function DashboardGenerateForm({ report, loading = false }: { report?: ReportDetail | null; loading?: boolean }) {
  const generation = useReportGeneration()
  const [period, setPeriod] = useState<ReportPeriod>(generation.lastRequest?.period ?? 'week')
  const [date, setDate] = useState(generation.lastRequest?.date ?? reportToday())
  const selectedPeriod = generation.pending ? generation.lastRequest?.period ?? period : period
  const selectedDate = generation.pending ? generation.lastRequest?.date ?? date : date
  const range = dashboardReportDateRange(selectedPeriod, selectedDate)
  const today = reportToday()
  const valid = range !== null && selectedDate <= today
  const changed = report && range && (report.week_start !== range.start || report.week_end !== range.end)
  const generate = (event: FormEvent) => {
    event.preventDefault()
    if (valid && !generation.pending && !loading) generation.generate({ period, date })
  }

  return (
    <form onSubmit={generate} className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-end gap-4">
        <fieldset disabled={generation.pending || loading} className="w-full min-w-0 sm:w-auto">
          <legend className="mb-2 text-control-label font-medium text-apple-mid">집계 단위</legend>
          <div className="grid grid-cols-3 rounded-xl bg-apple-gray p-1" aria-label="집계 단위">
            {(['week', 'month', 'year'] as const).map((value) => <button key={value} type="button" aria-pressed={selectedPeriod === value} onClick={() => setPeriod(value)} className={`rounded-lg px-5 py-2 text-control font-medium whitespace-nowrap transition-colors disabled:opacity-50 ${selectedPeriod === value ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>{REPORT_PERIOD_LABELS[value]}</button>)}
          </div>
        </fieldset>
        <label className="flex w-full min-w-0 flex-col gap-2 text-control-label font-medium text-apple-mid sm:w-auto">기준 날짜
          <input type="date" required max={today} value={selectedDate} disabled={generation.pending || loading} onChange={(event) => setDate(event.target.value)} className="min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30 disabled:opacity-50" />
        </label>
        <button type="submit" disabled={!valid || generation.pending || loading} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-control font-medium text-white whitespace-nowrap transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40 sm:ml-auto sm:w-auto">
          {generation.pending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}{generation.pending ? '집계 및 저장 중' : '보고서 생성'}
        </button>
      </div>
      {!valid && <p role="alert" className="mt-3 text-caption text-red-600">오늘 또는 이전의 유효한 날짜를 선택해 주세요.</p>}
      {changed && <p className="mt-3 text-caption font-medium text-brand-600">선택한 기간과 현재 보고서의 기간이 다릅니다. 새 조건으로 집계하려면 보고서를 생성하세요.</p>}
      {generation.pending && <p role="status" className="mt-3 text-label text-apple-mid">Jira 데이터를 집계하고 있습니다. 완료될 때까지 기존 보고서를 표시합니다.</p>}
      {generation.error && <p role="alert" className="mt-3 text-label text-red-600">{generation.error}</p>}
    </form>
  )
}
