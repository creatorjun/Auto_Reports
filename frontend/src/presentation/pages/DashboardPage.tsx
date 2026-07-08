// frontend/src/presentation/pages/DashboardPage.tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useLatestReport, useReportById } from '@/infrastructure/hooks/useReport'
import { useReportStore } from '@/app/store/reportStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SummaryCard from '@/presentation/components/cards/SummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import SlaDonutChart from '@/presentation/components/charts/SlaDonutChart'
import ReasonPieChart from '@/presentation/components/charts/ReasonPieChart'
import TypeBarChart from '@/presentation/components/charts/TypeBarChart'
import ResolutionTimeChart from '@/presentation/components/charts/ResolutionTimeChart'
import TrendLineChart from '@/presentation/components/charts/TrendLineChart'
import SlaMonthlyLineChart, { type MonthlyEntry } from '@/presentation/components/charts/SlaMonthlyLineChart'
import IssueDetailTable from '@/presentation/components/tables/IssueDetailTable'
import WeeklyCreatedModal, { type CreatedIssue } from '@/presentation/components/tables/WeeklyCreatedModal'
import WeeklyResolvedModal, { type ResolvedIssue } from '@/presentation/components/tables/WeeklyResolvedModal'
import IssueReviewModal, { type ReviewIssue } from '@/presentation/components/tables/IssueReviewModal'
import DataRequestModal, { type DataRequestIssue } from '@/presentation/components/tables/DataRequestModal'
import ResultPendingModal, { type ResultPendingIssue } from '@/presentation/components/tables/ResultPendingModal'
import type { ReportDetail } from '@/domain/Report'

interface SlaMonthlyBreakdown {
  monthly?: MonthlyEntry[]
  error?: string
}

interface ViolationEntry {
  stage: string
  count: number
  rate: number
}

interface W12Breakdown {
  '최초_응답_위반'?: number
  '해결_시간_위반'?: number
  _violation_distribution?: ViolationEntry[]
}

function DashboardContent({ report }: { report: ReportDetail }) {
  const { setCurrentReport } = useReportStore()
  const [showWeeklyCreated, setShowWeeklyCreated]   = useState(false)
  const [showWeeklyResolved, setShowWeeklyResolved] = useState(false)
  const [showIssueReview, setShowIssueReview]       = useState(false)
  const [showDataRequest, setShowDataRequest]       = useState(false)
  const [showResultPending, setShowResultPending]   = useState(false)

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const w      = report.widgets
  const w12    = (w.w12?.breakdown ?? {}) as W12Breakdown
  const w7     = w.w7?.breakdown  as Record<string, number> ?? {}
  const w10    = w.w10?.breakdown as Record<string, { avg_days: number; count: number }> ?? {}
  const w11    = w.w11?.breakdown as Record<string, unknown> ?? {}
  const w14    = w.w14?.breakdown as Record<string, unknown> ?? {}
  const w15    = (w.w15?.breakdown ?? {}) as unknown as SlaMonthlyBreakdown
  const w16    = (w.w16?.breakdown ?? {}) as unknown as SlaMonthlyBreakdown
  const details = (w11.issue_details ?? []) as Parameters<typeof IssueDetailTable>[0]['details']

  const w2Breakdown         = w.w2?.breakdown  as Record<string, unknown> ?? {}
  const w3Breakdown         = w.w3?.breakdown  as Record<string, unknown> ?? {}
  const w13Breakdown        = w.w13?.breakdown as Record<string, unknown> ?? {}
  const reviewIssues        = (w2Breakdown.issue_details  ?? []) as ReviewIssue[]
  const dataRequestIssues   = (w3Breakdown.issue_details  ?? []) as DataRequestIssue[]
  const resultPendingIssues = (w13Breakdown.issue_details ?? []) as ResultPendingIssue[]
  const weeklyCreated       = (w14.created_details  ?? []) as CreatedIssue[]
  const weeklyResolved      = (w14.resolved_details ?? []) as ResolvedIssue[]
  const w14Created          = (w14['생성'] ?? 0) as number
  const w14Resolved         = (w14['해결'] ?? 0) as number

  const w15Monthly = w15.monthly ?? []
  const w16Monthly = w16.monthly ?? []
  const hasW15 = w15Monthly.some((e) => e.total > 0)
  const hasW16 = w16Monthly.some((e) => e.total > 0)

  const w12Total        = w.w12?.total ?? 0
  const w12Distribution = w12._violation_distribution ?? []

  return (
    <div className="space-y-4 md:space-y-6 3xl:space-y-8">
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-7 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label="2026 생성" value={w.w8?.total ?? 0} color="gray" />
        <SummaryCard label="2026 해결" value={w.w9?.total ?? 0} color="gray" />
        <SummaryCard
          label="이번 주 생성"
          value={w14Created}
          color="blue"
          onClick={() => setShowWeeklyCreated(true)}
        />
        <SummaryCard
          label="이번 주 해결"
          value={w14Resolved}
          color="green"
          onClick={() => setShowWeeklyResolved(true)}
        />
        <SummaryCard
          label="이슈 리뷰 중"
          value={w.w2?.total ?? 0}
          color="yellow"
          onClick={() => setShowIssueReview(true)}
        />
        <SummaryCard
          label="자료 요청 중"
          value={w.w3?.total ?? 0}
          color="yellow"
          onClick={() => setShowDataRequest(true)}
        />
        <SummaryCard
          label="결과 대기 중"
          value={w.w13?.total ?? 0}
          color="yellow"
          onClick={() => setShowResultPending(true)}
        />
      </div>

      {/* 모달들 */}
      {showWeeklyCreated && (
        <WeeklyCreatedModal
          issues={weeklyCreated}
          total={w14Created}
          onClose={() => setShowWeeklyCreated(false)}
        />
      )}
      {showWeeklyResolved && (
        <WeeklyResolvedModal
          issues={weeklyResolved}
          total={w14Resolved}
          onClose={() => setShowWeeklyResolved(false)}
        />
      )}
      {showIssueReview && (
        <IssueReviewModal
          issues={reviewIssues}
          total={w.w2?.total ?? 0}
          onClose={() => setShowIssueReview(false)}
        />
      )}
      {showDataRequest && (
        <DataRequestModal
          issues={dataRequestIssues}
          total={w.w3?.total ?? 0}
          onClose={() => setShowDataRequest(false)}
        />
      )}
      {showResultPending && (
        <ResultPendingModal
          issues={resultPendingIssues}
          total={w.w13?.total ?? 0}
          onClose={() => setShowResultPending(false)}
        />
      )}

      {/* 월별 SLA 달성률 */}
      {(hasW15 || hasW16) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
          <SlaMonthlyLineChart
            title="✅ 최초응답 SLA"
            subtitle="최근 6개월 · 응답시간 위반 여부"
            monthly={w15Monthly}
            color="#3b82f6"
          />
          <SlaMonthlyLineChart
            title="✅ 해결시간 SLA"
            subtitle="최근 6개월 · 해결시간 위반 여부"
            monthly={w16Monthly}
            color="#22c55e"
          />
        </div>
      )}

      {/* 차트 행 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 3xl:gap-5">
        <SlaDonutChart total={w12Total} distribution={w12Distribution} />
        <ReasonPieChart breakdown={w7} />
        <div className="sm:col-span-2 md:col-span-1">
          <TrendLineChart created={w14Created} resolved={w14Resolved} />
        </div>
      </div>

      {/* 차트 행 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
        <TypeBarChart breakdown={w10} />
        <ResolutionTimeChart details={details} />
      </div>

      <IssueDetailTable details={details} />

      <div className="flex justify-end">
        <p className="text-[11px] 3xl:text-[12px] text-apple-light tabular-nums">
          {report.week_start} – {report.week_end}
          <span className="mx-1.5 text-apple-divider">·</span>
          생성: {report.report_date}
        </p>
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
  if (error)     return <div className="card text-[13px] text-red-500">데이터를 불러올 수 없습니다.</div>
  if (!data)     return (
    <div className="card text-[13px] text-apple-light text-center py-16">
      생성된 보고서가 없습니다. <span className="text-brand-600 font-medium">보고서 생성</span> 버튼을 놀러주세요.
    </div>
  )

  return <DashboardContent report={data} />
}
