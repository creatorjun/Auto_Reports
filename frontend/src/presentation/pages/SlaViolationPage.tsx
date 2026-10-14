// frontend/src/presentation/pages/SlaViolationPage.tsx
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CalendarDays, AlarmClock, History, Loader2, RefreshCw } from 'lucide-react'
import type { SlaViolationPeriod } from '@/domain/SlaViolationReport'
import { SLA_PERIOD_LABELS, slaDateRange, slaToday } from '@/application/services/slaViolationReport'
import { RequestError } from '@/application/errors/RequestError'
import { useGenerateSlaViolationReport, useSlaViolationReport } from '@/presentation/hooks/useSlaViolations'
import { useReportStore } from '@/presentation/state/reportStore'
import SlaViolationReportContent from '@/presentation/components/sla-violations/SlaViolationReportContent'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

function errorMessage(error: unknown): string {
  if (error instanceof RequestError && typeof error.detail === 'string') return error.detail
  return '보고서를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

export default function SlaViolationPage() {
  const { id } = useParams()
  const reportId = id === undefined ? undefined : Number(id)
  const invalidId = reportId !== undefined && (!Number.isSafeInteger(reportId) || reportId <= 0)
  const navigate = useNavigate()
  const [period, setPeriod] = useState<SlaViolationPeriod>('week')
  const [date, setDate] = useState(slaToday)
  const [loadedSource, setLoadedSource] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<number | null>(null)
  const query = useSlaViolationReport(reportId)
  const generation = useGenerateSlaViolationReport()
  const report = query.data
  const range = slaDateRange(period, date)
  const today = slaToday()
  const dateValid = range !== null && date <= today
  const changed = report && (report.period !== period || report.selected_date !== date)
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)

  useEffect(() => { setCurrentReport(null) }, [setCurrentReport, id])
  useEffect(() => {
    const source = report ? `${id ?? 'latest'}:${report.id}` : null
    if (report && source !== loadedSource) {
      setPeriod(report.period)
      setDate(report.selected_date)
      setLoadedSource(source)
    }
  }, [report, loadedSource, id])

  const generate = (event: React.FormEvent) => {
    event.preventDefault()
    if (!dateValid || generation.isPending) return
    setSavedId(null)
    generation.mutate({ period, date }, { onSuccess: (created) => {
      setSavedId(created.id)
      if (id !== undefined) navigate('/sla-violations')
    } })
  }

  return (
    <div className="mx-auto flex w-full max-w-content flex-col gap-5 3xl:max-w-none">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-caption font-medium text-brand-600"><AlarmClock size={16} />SLA 보고서</div>
          <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">SLA 위반</h1>
          <p className="mt-2 text-label text-apple-mid">선택한 기간에 생성된 티켓의 최초응답 위반과 해결 위반을 각각 확인합니다.</p>
        </div>
        <Link to="/history#sla-violations" className="flex items-center gap-2 rounded-xl border border-apple-divider bg-apple-surface px-4 py-2.5 text-control text-apple-mid hover:bg-apple-gray"><History size={16} />보고서 히스토리</Link>
      </header>

      <form onSubmit={generate} className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-end gap-4">
          <fieldset disabled={generation.isPending} className="min-w-0">
            <legend className="mb-2 text-control-label font-medium text-apple-mid">집계 단위</legend>
            <div className="inline-flex rounded-xl bg-apple-gray p-1" aria-label="집계 단위">
              {(['week', 'month', 'year'] as const).map((value) => <button key={value} type="button" aria-pressed={period === value} onClick={() => setPeriod(value)} className={`rounded-lg px-5 py-2 text-control font-medium transition-colors disabled:opacity-50 ${period === value ? 'bg-apple-surface text-brand-600 shadow-sm' : 'text-apple-mid hover:text-apple-dark'}`}>{SLA_PERIOD_LABELS[value]}</button>)}
            </div>
          </fieldset>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">기준 날짜
            <input type="date" required max={today} value={date} disabled={generation.isPending} onChange={(event) => setDate(event.target.value)} className="min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30 disabled:opacity-50" />
          </label>
          <button type="submit" disabled={!dateValid || generation.isPending || query.isFetching} className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-control font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40 sm:ml-auto">
            {generation.isPending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}{generation.isPending ? '집계 및 저장 중' : '보고서 생성'}
          </button>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-apple-divider/70 pt-3 text-caption text-apple-mid">
          <span className="flex items-center gap-1.5"><CalendarDays size={14} />집계 기간: {range ? `${range.start} – ${range.end}` : '기준 날짜를 선택해 주세요'}</span><span>주간: 월요일–일요일 · 한국 표준시 (KST)</span><span>생성 완료 시 히스토리에 자동 저장</span>
        </div>
        {!dateValid && <p role="alert" className="mt-3 text-caption text-red-600">오늘 또는 이전의 유효한 날짜를 선택해 주세요.</p>}
        {changed && <p className="mt-3 text-caption font-medium text-brand-600">생성 조건을 변경했습니다. 아래에는 기존 보고서가 표시됩니다. 새 조건으로 집계하려면 보고서를 생성하세요.</p>}
      </form>

      {generation.isPending && <p role="status" className="text-label text-apple-mid">Jira 이력과 SLA를 집계하고 있습니다. 티켓 수에 따라 몇 분 정도 걸릴 수 있습니다.</p>}
      {(query.isError || generation.isError || invalidId) && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-label text-red-700">{invalidId ? '올바르지 않은 보고서 주소입니다.' : errorMessage(generation.error ?? query.error)}{query.isError && <button type="button" disabled={generation.isPending} onClick={() => void query.refetch()} className="ml-3 underline">다시 불러오기</button>}</div>}
      {savedId === report?.id && <p role="status" className="text-label text-brand-600">보고서를 생성하고 히스토리에 저장했습니다.</p>}
      {query.isFetching && !report && !invalidId && <LoadingSpinner text="마지막 SLA 위반 보고서를 불러오는 중..." />}
      {report && <SlaViolationReportContent key={report.id} report={report} />}
      {!report && !query.isFetching && !query.isError && !invalidId && !generation.isPending && <div className="rounded-2xl border border-dashed border-apple-divider bg-apple-surface px-6 py-16 text-center"><AlarmClock size={32} className="mx-auto mb-4 text-brand-600" /><h2 className="text-section-title font-semibold text-apple-dark">아직 생성한 SLA 위반 보고서가 없습니다.</h2><p className="mt-2 text-label text-apple-mid">기간과 날짜를 선택하고 ‘보고서 생성’을 누르세요.<br />다음 방문부터 가장 최근 보고서를 자동으로 보여드립니다.</p></div>}
    </div>
  )
}
