// frontend/src/presentation/components/common/DashboardGenerateForm.tsx
import { useState, type FormEvent } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import type { DashboardReportPeriod, DashboardReportRequest } from '@/domain/ReportPeriod'
import type { ReportDetail } from '@/domain/Report'
import { DASHBOARD_REPORT_PERIOD_LABELS, dashboardReportDateRange, reportToday } from '@/application/services/reportPeriod'
import { useReportGeneration } from '@/presentation/context/ReportGenerationContext'

export default function DashboardGenerateForm({ report, loading = false }: { report?: ReportDetail | null; loading?: boolean }) {
  const generation = useReportGeneration()
  const lastRequest = generation.lastRequest
  const [period, setPeriod] = useState<DashboardReportPeriod>(lastRequest?.period ?? 'week')
  const [date, setDate] = useState(lastRequest && lastRequest.period !== 'custom' ? lastRequest.date : reportToday())
  const [startDate, setStartDate] = useState(lastRequest?.period === 'custom' ? lastRequest.start_date : reportToday())
  const [endDate, setEndDate] = useState(lastRequest?.period === 'custom' ? lastRequest.end_date : reportToday())
  const draftRequest: DashboardReportRequest = period === 'custom'
    ? { period, start_date: startDate, end_date: endDate }
    : { period, date }
  const selectedRequest = generation.pending ? lastRequest ?? draftRequest : draftRequest
  const selectedPeriod = selectedRequest.period
  const today = reportToday()
  const range = dashboardReportDateRange(selectedRequest, today)
  const valid = range !== null
  const changed = report && range && (report.week_start !== range.start || report.week_end !== range.end)
  const generate = (event: FormEvent) => {
    event.preventDefault()
    if (valid && !generation.pending && !loading) generation.generate(draftRequest)
  }

  return (
    <form onSubmit={generate} className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-end gap-4">
        <fieldset disabled={generation.pending || loading} className="w-full min-w-0 sm:w-auto">
          <legend className="mb-2 text-control-label font-medium text-apple-mid">집계 단위</legend>
          <div className="grid grid-cols-4 rounded-xl bg-apple-gray p-1 sm:grid-cols-5" aria-label="집계 단위">
            {(['day', 'week', 'month', 'year', 'custom'] as const).map((value) => <button key={value} type="button" aria-pressed={selectedPeriod === value} onClick={() => setPeriod(value)} className={`min-w-0 rounded-lg px-2 py-2 text-control font-medium whitespace-nowrap transition-colors disabled:opacity-50 sm:px-5 ${value === 'custom' ? 'col-span-4 sm:col-span-1' : ''} ${selectedPeriod === value ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>{DASHBOARD_REPORT_PERIOD_LABELS[value]}</button>)}
          </div>
        </fieldset>
        {selectedRequest.period === 'custom' ? (
          <div className="grid w-full min-w-0 grid-cols-1 gap-4 sm:w-auto sm:grid-cols-2">
            <label className="flex min-w-0 flex-col gap-2 text-control-label font-medium text-apple-mid">시작 날짜
              <input type="date" required max={today} aria-label="시작 날짜" value={selectedRequest.start_date} disabled={generation.pending || loading} onChange={(event) => setStartDate(event.target.value)} className="min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30 disabled:opacity-50" />
            </label>
            <label className="flex min-w-0 flex-col gap-2 text-control-label font-medium text-apple-mid">종료 날짜
              <input type="date" required min={selectedRequest.start_date || undefined} max={today} aria-label="종료 날짜" value={selectedRequest.end_date} disabled={generation.pending || loading} onChange={(event) => setEndDate(event.target.value)} className="min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30 disabled:opacity-50" />
            </label>
          </div>
        ) : (
          <label className="flex w-full min-w-0 flex-col gap-2 text-control-label font-medium text-apple-mid sm:w-auto">기준 날짜
            <input type="date" required max={today} value={selectedRequest.date} disabled={generation.pending || loading} onChange={(event) => setDate(event.target.value)} className="min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30 disabled:opacity-50" />
          </label>
        )}
        <button type="submit" disabled={!valid || generation.pending || loading} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-control font-medium text-white whitespace-nowrap transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40 sm:ml-auto sm:w-auto">
          {generation.pending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}{generation.pending ? '집계 및 저장 중' : '보고서 생성'}
        </button>
      </div>
      {!valid && <p role="alert" className="mt-3 text-caption text-red-600">{selectedPeriod === 'custom' ? '오늘 또는 이전의 유효한 시작·종료 날짜를 선택해 주세요. 종료 날짜는 시작 날짜보다 빠를 수 없습니다.' : '오늘 또는 이전의 유효한 날짜를 선택해 주세요.'}</p>}
      {selectedPeriod === 'custom' && <p className="mt-3 text-caption text-apple-mid">한국 시간 기준으로 시작 날짜부터 종료 날짜까지 포함합니다.</p>}
      {changed && <p className="mt-3 text-caption font-medium text-brand-600">선택한 기간과 현재 보고서의 기간이 다릅니다. 새 조건으로 집계하려면 보고서를 생성하세요.</p>}
      {generation.pending && <p role="status" className="mt-3 text-label text-apple-mid">Jira 데이터를 집계하고 있습니다. 완료될 때까지 기존 보고서를 표시합니다.</p>}
      {generation.error && <p role="alert" className="mt-3 text-label text-red-600">{generation.error}</p>}
    </form>
  )
}
