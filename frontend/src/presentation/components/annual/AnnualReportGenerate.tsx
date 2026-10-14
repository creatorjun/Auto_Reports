// frontend/src/presentation/components/annual/AnnualReportGenerate.tsx
import { CalendarRange, Loader2, RefreshCw } from 'lucide-react'
import { reportToday } from '@/application/services/reportPeriod'
import { useReportGeneration } from '@/presentation/context/ReportGenerationContext'

export default function AnnualReportGenerate({ year, loading = false }: { year: number; loading?: boolean }) {
  const generation = useReportGeneration()
  const today = reportToday()
  const start = `${year}-01-01`
  const end = year === Number(today.slice(0, 4)) ? today : `${year}-12-31`
  const valid = Number.isSafeInteger(year) && year > 0 && year <= Number(today.slice(0, 4))

  return (
    <div className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-page-title font-semibold text-apple-dark"><CalendarRange size={18} />{year} 연간 보고서</h1>
          <p className="mt-2 text-caption text-apple-mid">집계 기간: {start} – {end} · 한국 표준시 (KST)</p>
        </div>
        <button type="button" disabled={!valid || loading || generation.pending} onClick={() => generation.generate({ start_date: start, end_date: end })} className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-control font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40">
          {generation.pending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}{generation.pending ? '집계 및 저장 중' : '연간 보고서 생성'}
        </button>
      </div>
      {generation.pending && <p role="status" className="mt-3 text-label text-apple-mid">보고서를 집계하고 있습니다. 완료되면 히스토리에 자동 저장합니다.</p>}
      {generation.error && <p role="alert" className="mt-3 text-label text-red-600">{generation.error}</p>}
    </div>
  )
}
