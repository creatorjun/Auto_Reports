// frontend/src/presentation/components/sla-violations/SlaViolationHistory.tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, AlarmClock, RefreshCw } from 'lucide-react'
import { SLA_PERIOD_LABELS } from '@/application/services/slaViolationReport'
import { useSlaViolationHistory } from '@/presentation/hooks/useSlaViolations'
import { slaTimestamp } from '@/presentation/utils/slaViolationFormatters'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

const PAGE_SIZE = 20

export default function SlaViolationHistory() {
  const [page, setPage] = useState(0)
  const history = useSlaViolationHistory(page, PAGE_SIZE)
  const reports = history.data ?? []
  return (
    <section id="sla-violations" aria-labelledby="sla-history-title" className="scroll-mt-6 border-t border-apple-divider pt-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><h2 id="sla-history-title" className="flex items-center gap-2 text-section-title font-semibold text-apple-dark"><AlarmClock size={18} />SLA 위반 보고서</h2><p className="mt-1 text-caption text-apple-mid">생성할 때마다 저장된 보고서 · 최신 생성순</p></div>
        <div className="flex items-center gap-3"><button type="button" aria-label="SLA 위반 히스토리 새로고침" onClick={() => void history.refetch()} disabled={history.isFetching} className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray disabled:opacity-40"><RefreshCw size={16} /></button><Link to="/sla-violations" className="text-label font-medium text-brand-600 hover:underline">보고서 생성</Link></div>
      </div>
      {history.isError && <div role="alert" className="mb-3 rounded-xl bg-red-50 p-4 text-label text-red-700">SLA 위반 히스토리를 불러오지 못했습니다.<button type="button" onClick={() => void history.refetch()} className="ml-2 underline">다시 시도</button></div>}
      <div className="overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm">
        {history.isLoading ? <div className="py-10"><LoadingSpinner /></div> : reports.length > 0 ? (
          <ul className="divide-y divide-apple-divider/70">{reports.map((report) => (
            <li key={report.id}><Link to={`/sla-violations/history/${report.id}`} className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-apple-gray sm:flex-row sm:items-center sm:justify-between">
              <div><div className="flex flex-wrap items-center gap-2"><span className="rounded-md bg-apple-gray px-2 py-1 text-caption font-medium text-brand-600">{SLA_PERIOD_LABELS[report.period]}</span><span className="text-label font-semibold text-apple-dark">{report.start_date} – {report.end_date}</span></div><p className="mt-2 text-caption text-apple-mid">{slaTimestamp(report.generated_at)} KST · {report.generated_by} · #{report.id}</p></div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-apple-mid"><span>최초응답 <strong className="text-apple-dark">{report.initial_response_count.toLocaleString('ko-KR')}건</strong></span><span>해결 <strong className="text-apple-dark">{report.resolution_count.toLocaleString('ko-KR')}건</strong></span><span>총 <strong className="text-apple-dark">{report.ticket_count.toLocaleString('ko-KR')}개 티켓</strong></span></div>
            </Link></li>
          ))}</ul>
        ) : !history.isError && <p className="py-12 text-center text-label text-apple-mid">{page === 0 ? '아직 저장된 SLA 위반 보고서가 없습니다.' : '마지막 페이지입니다. 이전 페이지에서 보고서를 확인해 주세요.'}</p>}
      </div>
      {(page > 0 || reports.length >= PAGE_SIZE) && <div className="mt-4 flex items-center justify-between text-caption text-apple-mid">
        <button type="button" onClick={() => setPage((value) => value - 1)} disabled={page === 0 || history.isFetching} className="flex items-center gap-1 rounded-xl bg-apple-gray px-3 py-2 disabled:opacity-40"><ChevronLeft size={14} />이전</button><span>SLA 위반 · {page + 1} 페이지</span><button type="button" onClick={() => setPage((value) => value + 1)} disabled={reports.length < PAGE_SIZE || history.isFetching} className="flex items-center gap-1 rounded-xl bg-apple-gray px-3 py-2 disabled:opacity-40">다음<ChevronRight size={14} /></button>
      </div>}
    </section>
  )
}
