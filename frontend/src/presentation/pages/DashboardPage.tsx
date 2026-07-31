// frontend/src/presentation/pages/DashboardPage.tsx
import { lazy, Suspense, useEffect, useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useLatestReport, useReportById } from '@/infrastructure/hooks/useReport'
import { useReportStore } from '@/app/store/reportStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SummaryCard from '@/presentation/components/cards/SummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import { MONTHLY_COUNT_COLORS, SLA_MONTHLY_COLORS } from '@/shared/constants'
import type { ReportDetail } from '@/domain/Report'
import type { RecentIssue } from '@/domain/Issue'

const SlaDonutChart       = lazy(() => import('@/presentation/components/charts/SlaDonutChart'))
const ReasonPieChart      = lazy(() => import('@/presentation/components/charts/ReasonPieChart'))
const TypeBarChart        = lazy(() => import('@/presentation/components/charts/TypeBarChart'))
const ResolutionTimeChart = lazy(() => import('@/presentation/components/charts/ResolutionTimeChart'))
const TrendLineChart      = lazy(() => import('@/presentation/components/charts/TrendLineChart'))
const SlaMonthlyLineChart = lazy(() => import('@/presentation/components/charts/SlaMonthlyLineChart'))
const MonthlyCountChart   = lazy(() => import('@/presentation/components/charts/MonthlyCountChart'))

const WeeklyCreatedModal  = lazy(() => import('@/presentation/components/tables/WeeklyCreatedModal'))
const WeeklyResolvedModal = lazy(() => import('@/presentation/components/tables/WeeklyResolvedModal'))
const IssueReviewModal    = lazy(() => import('@/presentation/components/tables/IssueReviewModal'))
const DataRequestModal    = lazy(() => import('@/presentation/components/tables/DataRequestModal'))
const ResultPendingModal  = lazy(() => import('@/presentation/components/tables/ResultPendingModal'))
const IncompleteIssueModal = lazy(() => import('@/presentation/components/tables/IncompleteIssueModal'))
const SlaViolationModal   = lazy(() => import('@/presentation/components/tables/SlaViolationModal'))
const SlaDelayModal       = lazy(() => import('@/presentation/components/tables/SlaDelayModal'))

import type { ViolationEntry } from '@/presentation/components/charts/SlaDonutChart'
import type { SlaDelayIssue } from '@/presentation/components/charts/ReasonPieChart'
import type { MonthlyEntry } from '@/presentation/components/charts/SlaMonthlyLineChart'
import type { MonthlyCountEntry } from '@/presentation/components/charts/MonthlyCountChart'
import type { CreatedIssue } from '@/presentation/components/tables/WeeklyCreatedModal'
import type { ResolvedIssue } from '@/presentation/components/tables/WeeklyResolvedModal'
import type { ReviewIssue } from '@/presentation/components/tables/IssueReviewModal'
import type { DataRequestIssue } from '@/presentation/components/tables/DataRequestModal'
import type { ResultPendingIssue } from '@/presentation/components/tables/ResultPendingModal'
import type { IncompleteIssue } from '@/presentation/components/tables/IncompleteIssueModal'
import type { SlaViolationIssue } from '@/presentation/components/tables/SlaViolationModal'

const ModalFallback = () => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-8 flex items-center justify-center">
      <LoadingSpinner text="로딩 중..." />
    </div>
  </div>
)

const ChartFallback = () => (
  <div className="flex items-center justify-center h-40 rounded-xl bg-gray-50">
    <LoadingSpinner text="" />
  </div>
)

interface W9Data {
  initial_response_violations?: number
  resolution_violations?: number
  violation_distribution?: ViolationEntry[]
}

interface W10Data {
  by_status?: Record<string, number>
  by_status_details?: Record<string, SlaDelayIssue[]>
}

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

function getData<T>(widget: { data: Record<string, unknown> | null } | undefined): T | null {
  return (widget?.data ?? null) as T | null
}

function DashboardContent({ report }: { report: ReportDetail }) {
  const { setCurrentReport } = useReportStore()
  const [showWeeklyCreated,   setShowWeeklyCreated]   = useState(false)
  const [showWeeklyResolved,  setShowWeeklyResolved]  = useState(false)
  const [showIssueReview,     setShowIssueReview]     = useState(false)
  const [showDataRequest,     setShowDataRequest]     = useState(false)
  const [showResultPending,   setShowResultPending]   = useState(false)
  const [showIncomplete,      setShowIncomplete]      = useState(false)
  const [slaViolationEntry,   setSlaViolationEntry]   = useState<ViolationEntry | null>(null)
  const [slaDelayEntry,       setSlaDelayEntry]       = useState<{ status: string; issues: SlaDelayIssue[] } | null>(null)

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const w = report.widgets

  const { w3Created, w3Resolved, weeklyCreated, weeklyResolved, dateRange } = useMemo(() => {
    const w3Data = getData<{ created: number; resolved: number; created_details: CreatedIssue[]; resolved_details: ResolvedIssue[] }>(w.w3)
    return {
      w3Created:      w3Data?.created          ?? 0,
      w3Resolved:     w3Data?.resolved         ?? 0,
      weeklyCreated:  w3Data?.created_details  ?? [],
      weeklyResolved: w3Data?.resolved_details ?? [],
      dateRange: report.week_start && report.week_end ? { start: report.week_start, end: report.week_end } : undefined,
    }
  }, [w.w3, report.week_start, report.week_end])

  const { w7Monthly, w8Monthly, hasW7, hasW8 } = useMemo(() => {
    const w7Data = getData<{ monthly: MonthlyEntry[] }>(w.w7)
    const w8Data = getData<{ monthly: MonthlyEntry[] }>(w.w8)
    const w7Monthly = w7Data?.monthly ?? []
    const w8Monthly = w8Data?.monthly ?? []
    return { w7Monthly, w8Monthly, hasW7: w7Monthly.some((e) => e.total > 0), hasW8: w8Monthly.some((e) => e.total > 0) }
  }, [w.w7, w.w8])

  const { w13Monthly, w14Monthly, hasW13, hasW14 } = useMemo(() => {
    const w13Data = getData<{ monthly: MonthlyCountEntry[] }>(w.w13)
    const w14Data = getData<{ monthly: MonthlyCountEntry[] }>(w.w14)
    const w13Monthly = w13Data?.monthly ?? []
    const w14Monthly = w14Data?.monthly ?? []
    return { w13Monthly, w14Monthly, hasW13: w13Monthly.some((e) => e.count > 0), hasW14: w14Monthly.some((e) => e.count > 0) }
  }, [w.w13, w.w14])

  const { w9Total, w9Distribution } = useMemo(() => {
    const w9Data = getData<W9Data>(w.w9)
    return { w9Total: w.w9?.total ?? 0, w9Distribution: w9Data?.violation_distribution ?? [] }
  }, [w.w9])

  const { w10ByStatus, w10ByStatusDetails } = useMemo(() => {
    const w10Data = getData<W10Data>(w.w10)
    return {
      w10ByStatus:        w10Data?.by_status         ?? {},
      w10ByStatusDetails: w10Data?.by_status_details ?? {},
    }
  }, [w.w10])

  const w11ByType = useMemo(() => {
    const w11Data = getData<{ by_type: Record<string, ResolutionTypeEntry> }>(w.w11)
    return w11Data?.by_type ?? {}
  }, [w.w11])

  const { recentIssues, incompleteIssues, incompleteTotal } = useMemo(() => {
    const w12Data = getData<{ issue_details: RecentIssue[] }>(w.w12)
    const recentIssues = (w12Data?.issue_details ?? []).map((i) => ({ ...i, reporter: i.reporter ?? '미지정', tac_team: i.tac_team ?? '미지정' }))
    const incompleteIssues: IncompleteIssue[] = recentIssues.map((i) => ({ key: i.key, summary: i.summary, type: i.type, status: i.status, created: i.created, elapsed_days: i.elapsed_days }))
    return { recentIssues, incompleteIssues, incompleteTotal: incompleteIssues.length }
  }, [w.w12])

  const { reviewIssues, dataRequestIssues, resultPendingIssues } = useMemo(() => {
    const w4Data = getData<{ issue_details: ReviewIssue[] }>(w.w4)
    const w5Data = getData<{ issue_details: DataRequestIssue[] }>(w.w5)
    const w6Data = getData<{ issue_details: ResultPendingIssue[] }>(w.w6)
    return { reviewIssues: w4Data?.issue_details ?? [], dataRequestIssues: w5Data?.issue_details ?? [], resultPendingIssues: w6Data?.issue_details ?? [] }
  }, [w.w4, w.w5, w.w6])

  const slaModalIssues: SlaViolationIssue[] = useMemo(() => {
    if (!slaViolationEntry) return []
    return (slaViolationEntry.issue_details ?? []) as SlaViolationIssue[]
  }, [slaViolationEntry])

  const handleTrendBarClick = (key: '생성' | '해결') => {
    if (key === '생성') setShowWeeklyCreated(true)
    else setShowWeeklyResolved(true)
  }

  return (
    <div className="space-y-4 md:space-y-6 3xl:space-y-8">
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}
      <div className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-8 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label={`${new Date().getFullYear()} 생성`} value={w.w1?.total ?? 0} color="gray" />
        <SummaryCard label={`${new Date().getFullYear()} 해결`} value={w.w2?.total ?? 0} color="gray" />
        <SummaryCard label="생성"         value={w3Created}        color="blue"   onClick={() => setShowWeeklyCreated(true)}  />
        <SummaryCard label="완료"         value={w3Resolved}       color="green"  onClick={() => setShowWeeklyResolved(true)} />
        <SummaryCard label="이슈 리뷰 중" value={w.w4?.total ?? 0} color="yellow" onClick={() => setShowIssueReview(true)}    />
        <SummaryCard label="자료 요청 중" value={w.w5?.total ?? 0} color="yellow" onClick={() => setShowDataRequest(true)}    />
        <SummaryCard label="결과 대기 중" value={w.w6?.total ?? 0} color="yellow" onClick={() => setShowResultPending(true)}  />
        <SummaryCard label="미완료 이슈"  value={incompleteTotal}  color="red"    onClick={() => setShowIncomplete(true)}     />
      </div>

      {showWeeklyCreated && (
        <Suspense fallback={<ModalFallback />}>
          <WeeklyCreatedModal issues={weeklyCreated} total={w3Created} dateRange={dateRange} onClose={() => setShowWeeklyCreated(false)} />
        </Suspense>
      )}
      {showWeeklyResolved && (
        <Suspense fallback={<ModalFallback />}>
          <WeeklyResolvedModal issues={weeklyResolved} total={w3Resolved} dateRange={dateRange} onClose={() => setShowWeeklyResolved(false)} />
        </Suspense>
      )}
      {showIssueReview && (
        <Suspense fallback={<ModalFallback />}>
          <IssueReviewModal issues={reviewIssues} total={w.w4?.total ?? 0} onClose={() => setShowIssueReview(false)} />
        </Suspense>
      )}
      {showDataRequest && (
        <Suspense fallback={<ModalFallback />}>
          <DataRequestModal issues={dataRequestIssues} total={w.w5?.total ?? 0} onClose={() => setShowDataRequest(false)} />
        </Suspense>
      )}
      {showResultPending && (
        <Suspense fallback={<ModalFallback />}>
          <ResultPendingModal issues={resultPendingIssues} total={w.w6?.total ?? 0} onClose={() => setShowResultPending(false)} />
        </Suspense>
      )}
      {showIncomplete && (
        <Suspense fallback={<ModalFallback />}>
          <IncompleteIssueModal issues={incompleteIssues} total={incompleteTotal} onClose={() => setShowIncomplete(false)} />
        </Suspense>
      )}
      {slaViolationEntry && (
        <Suspense fallback={<ModalFallback />}>
          <SlaViolationModal
            stage={slaViolationEntry.stage}
            issues={slaModalIssues}
            total={slaViolationEntry.count}
            onClose={() => setSlaViolationEntry(null)}
          />
        </Suspense>
      )}
      {slaDelayEntry && (
        <Suspense fallback={<ModalFallback />}>
          <SlaDelayModal
            status={slaDelayEntry.status}
            issues={slaDelayEntry.issues}
            total={slaDelayEntry.issues.length}
            onClose={() => setSlaDelayEntry(null)}
          />
        </Suspense>
      )}

      {(hasW13 || hasW14) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
          <Suspense fallback={<ChartFallback />}>
            <MonthlyCountChart title="📋 월별 등록 건수" subtitle="최근 6개월" monthly={w13Monthly} color={MONTHLY_COUNT_COLORS.created}  />
          </Suspense>
          <Suspense fallback={<ChartFallback />}>
            <MonthlyCountChart title="✅ 월별 해결 건수" subtitle="최근 6개월" monthly={w14Monthly} color={MONTHLY_COUNT_COLORS.resolved} />
          </Suspense>
        </div>
      )}
      {(hasW7 || hasW8) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
          <Suspense fallback={<ChartFallback />}>
            <SlaMonthlyLineChart title="✅ 최초응답 SLA" subtitle="최근 6개월 · 응답시간 위반 여부" monthly={w7Monthly} color={SLA_MONTHLY_COLORS.initial}    />
          </Suspense>
          <Suspense fallback={<ChartFallback />}>
            <SlaMonthlyLineChart title="✅ 해결시간 SLA" subtitle="최근 6개월 · 해결시간 위반 여부" monthly={w8Monthly} color={SLA_MONTHLY_COLORS.resolution} />
          </Suspense>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4 3xl:gap-5">
        <Suspense fallback={<ChartFallback />}>
          <SlaDonutChart
            total={w9Total}
            distribution={w9Distribution}
            onSliceClick={(entry) => setSlaViolationEntry(entry)}
          />
        </Suspense>
        <Suspense fallback={<ChartFallback />}>
          <ReasonPieChart
            byStatus={w10ByStatus}
            byStatusDetails={w10ByStatusDetails}
            onSliceClick={(status, issues) => setSlaDelayEntry({ status, issues })}
          />
        </Suspense>
        <Suspense fallback={<ChartFallback />}>
          <TrendLineChart
            created={w3Created}
            resolved={w3Resolved}
            onBarClick={handleTrendBarClick}
          />
        </Suspense>
        <Suspense fallback={<ChartFallback />}>
          <TypeBarChart byType={w11ByType} />
        </Suspense>
      </div>
      <Suspense fallback={<ChartFallback />}>
        <ResolutionTimeChart details={recentIssues} />
      </Suspense>
    </div>
  )
}

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>()
  const latestQuery = useLatestReport()
  const byIdQuery   = useReportById(Number(id))
  const { data, isLoading, error } = id ? byIdQuery : latestQuery

  if (isLoading) return <LoadingSpinner text="보고서 로딩 중..." />
  if (error)     return <div className="card text-ui-base text-red-500">데이터를 불러올 수 없습니다.</div>
  if (!data)     return (
    <div className="card text-ui-base text-apple-light text-center py-16">
      생성된 보고서가 없습니다. <span className="text-brand-600 font-medium">보고서 생성</span> 버튼을 누르세요.
    </div>
  )
  return <DashboardContent report={data} />
}
