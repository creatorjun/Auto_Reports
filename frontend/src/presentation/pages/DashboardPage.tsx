// frontend/src/presentation/pages/DashboardPage.tsx
import { lazy, Suspense, useEffect, useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { BarChart2, ShieldAlert, Activity, Pin } from 'lucide-react'
import { useLatestReport, useReportById } from '@/infrastructure/hooks/useReport'
import { useReportStore } from '@/app/store/reportStore'
import { useDashboardData } from '@/infrastructure/hooks/useDashboardData'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SummaryCard, { SUMMARY_ICONS } from '@/presentation/components/cards/SummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import SectionTitle from '@/presentation/components/common/SectionTitle'
import { ModalFallback, ChartFallback } from '@/presentation/components/common/DashboardFallbacks'
import { MONTHLY_COUNT_COLORS, SLA_MONTHLY_COLORS } from '@/shared/constants'
import type { ReportDetail } from '@/domain/Report'
import type { ViolationEntry } from '@/presentation/components/charts/SlaDonutChart'
import type { SlaDelayIssue } from '@/presentation/components/charts/ReasonPieChart'
import type { SlaViolationIssue } from '@/presentation/components/tables/SlaViolationModal'

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

function DashboardContent({ report }: { report: ReportDetail }) {
  const { setCurrentReport } = useReportStore()
  const [showWeeklyCreated,  setShowWeeklyCreated]  = useState(false)
  const [showWeeklyResolved, setShowWeeklyResolved] = useState(false)
  const [showIssueReview,    setShowIssueReview]    = useState(false)
  const [showDataRequest,    setShowDataRequest]    = useState(false)
  const [showResultPending,  setShowResultPending]  = useState(false)
  const [showIncomplete,     setShowIncomplete]     = useState(false)
  const [slaViolationEntry,  setSlaViolationEntry]  = useState<ViolationEntry | null>(null)
  const [slaDelayEntry,      setSlaDelayEntry]      = useState<{ status: string; issues: SlaDelayIssue[] } | null>(null)

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const { weekly, slaMonthly, monthlyCount, slaDonut, slaDelay, resolutionByType, recentAndIncomplete, statusIssues } = useDashboardData(report)
  const { w3Created, w3Resolved, weeklyCreated, weeklyResolved, dateRange } = weekly
  const { w7Monthly, w8Monthly, hasW7, hasW8 } = slaMonthly
  const { w13Monthly, w14Monthly, hasW13, hasW14 } = monthlyCount
  const { w9Total, w9Distribution } = slaDonut
  const { w10ByStatus, w10ByStatusDetails } = slaDelay
  const { recentIssues, incompleteIssues, incompleteTotal } = recentAndIncomplete
  const { reviewIssues, dataRequestIssues, resultPendingIssues } = statusIssues
  const w = report.widgets

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
        <SummaryCard label={`${new Date().getFullYear()} 생성`} value={w.w1?.total ?? 0} color="gray"   icon={SUMMARY_ICONS.yearCreated}   />
        <SummaryCard label={`${new Date().getFullYear()} 해결`} value={w.w2?.total ?? 0} color="gray"   icon={SUMMARY_ICONS.yearResolved}   />
        <SummaryCard label="생성"         value={w3Created}        color="blue"   icon={SUMMARY_ICONS.weekCreated}   onClick={() => setShowWeeklyCreated(true)}  />
        <SummaryCard label="완료"         value={w3Resolved}       color="green"  icon={SUMMARY_ICONS.weekResolved}   onClick={() => setShowWeeklyResolved(true)} />
        <SummaryCard label="이슈 리뷰 중" value={w.w4?.total ?? 0} color="yellow" icon={SUMMARY_ICONS.issueReview}    onClick={() => setShowIssueReview(true)}    />
        <SummaryCard label="자료 요청 중" value={w.w5?.total ?? 0} color="yellow" icon={SUMMARY_ICONS.dataRequest}    onClick={() => setShowDataRequest(true)}    />
        <SummaryCard label="결과 대기 중" value={w.w6?.total ?? 0} color="yellow" icon={SUMMARY_ICONS.resultPending}  onClick={() => setShowResultPending(true)}  />
        <SummaryCard label="미완료 이슈"  value={incompleteTotal}  color="red"    icon={SUMMARY_ICONS.incomplete}     onClick={() => setShowIncomplete(true)}     />
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
        <div className="space-y-1">
          <SectionTitle icon={BarChart2} title="월별 이슈 현황" subtitle="최근 6개월" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
            <Suspense fallback={<ChartFallback />}>
              <MonthlyCountChart title="월별 등록 건수" subtitle="최근 6개월" monthly={w13Monthly} color={MONTHLY_COUNT_COLORS.created}  />
            </Suspense>
            <Suspense fallback={<ChartFallback />}>
              <MonthlyCountChart title="월별 해결 건수" subtitle="최근 6개월" monthly={w14Monthly} color={MONTHLY_COUNT_COLORS.resolved} />
            </Suspense>
          </div>
        </div>
      )}
      {(hasW7 || hasW8) && (
        <div className="space-y-1">
          <SectionTitle icon={ShieldAlert} title="SLA 준수율" subtitle="최근 6개월" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
            <Suspense fallback={<ChartFallback />}>
              <SlaMonthlyLineChart title="최초응답 SLA" subtitle="최근 6개월 · 응답시간 위반 여부" monthly={w7Monthly} color={SLA_MONTHLY_COLORS.initial}    />
            </Suspense>
            <Suspense fallback={<ChartFallback />}>
              <SlaMonthlyLineChart title="해결시간 SLA" subtitle="최근 6개월 · 해결시간 위반 여부" monthly={w8Monthly} color={SLA_MONTHLY_COLORS.resolution} />
            </Suspense>
          </div>
        </div>
      )}
      <div className="space-y-1">
        <SectionTitle icon={Activity} title="분석 차트" />
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
            <TypeBarChart byType={resolutionByType} />
          </Suspense>
        </div>
      </div>
      <div className="space-y-1">
        <SectionTitle icon={Pin} title="최근 이슈 현황" subtitle={`최신 ${recentIssues.length}건`} />
        <Suspense fallback={<ChartFallback />}>
          <ResolutionTimeChart details={recentIssues} />
        </Suspense>
      </div>
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
