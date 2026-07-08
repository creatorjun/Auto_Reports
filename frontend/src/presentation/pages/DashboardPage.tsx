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

// ---------- 로컬 타입 ----------
interface ViolationEntry {
  stage: string
  count: number
  rate: number
}

interface W9Data {
  initial_response_violations?: number
  resolution_violations?: number
  violation_distribution?: ViolationEntry[]
}

interface RecentIssue {
  key: string
  summary: string
  type: string
  status: string
  stage_index: number
  created: string
  elapsed_days: number
}

interface ResolutionTypeEntry {
  avg_days: number
  avg_hours: number
  count: number
}

// ---------- 헬퍼: data 필드를 안전하게 꼼내는 유틸 ----------
function getData<T>(widget: { data: Record<string, unknown> | null } | undefined): T | null {
  return (widget?.data ?? null) as T | null
}

function DashboardContent({ report }: { report: ReportDetail }) {
  const { setCurrentReport } = useReportStore()
  const [showWeeklyCreated,  setShowWeeklyCreated]  = useState(false)
  const [showWeeklyResolved, setShowWeeklyResolved] = useState(false)
  const [showIssueReview,    setShowIssueReview]    = useState(false)
  const [showDataRequest,    setShowDataRequest]    = useState(false)
  const [showResultPending,  setShowResultPending]  = useState(false)

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const w = report.widgets

  // ── w4 : SLA 지연 사유 (SlaDelayWidgetData) ───────────────────────────
  const w4Data      = getData<{ by_status: Record<string, number> }>(w.w4)
  const w4ByStatus  = w4Data?.by_status ?? {}

  // ── w7 : 유형별 평균 처리일 (ResolutionTypeWidgetData) ─────────────────
  const w7Data   = getData<{ by_type: Record<string, ResolutionTypeEntry> }>(w.w7)
  const w7ByType = w7Data?.by_type ?? {}

  // ── w8 : 최근 이슈 (RecentIssueWidgetData) ─────────────────────────────
  const w8Data      = getData<{ issue_details: RecentIssue[] }>(w.w8)
  const recentIssues = w8Data?.issue_details ?? []

  // ── w9 : SLA 준수 vs 위반 (SlaMetVsViolatedWidgetData) ─────────────────
  const w9Data         = getData<W9Data>(w.w9)
  const w9Total        = w.w9?.total ?? 0
  const w9Distribution = w9Data?.violation_distribution ?? []

  // ── w11 : 주간 생성/해결 (CreatedVsResolvedWidgetData) ────────────────
  const w11Data     = getData<{
    created: number
    resolved: number
    created_details: CreatedIssue[]
    resolved_details: ResolvedIssue[]
  }>(w.w11)
  const w11Created       = w11Data?.created          ?? 0
  const w11Resolved      = w11Data?.resolved         ?? 0
  const weeklyCreated    = w11Data?.created_details  ?? []
  const weeklyResolved   = w11Data?.resolved_details ?? []

  // ── w12 / w13 : 월별 SLA (SlaMonthlyWidgetData) ───────────────────────
  const w12Data    = getData<{ monthly: MonthlyEntry[] }>(w.w12)
  const w13Data    = getData<{ monthly: MonthlyEntry[] }>(w.w13)
  const w12Monthly = w12Data?.monthly ?? []
  const w13Monthly = w13Data?.monthly ?? []
  const hasW12     = w12Monthly.some((e) => e.total > 0)
  const hasW13     = w13Monthly.some((e) => e.total > 0)

  // ── w1 : 지연 이슈 상세 (OverdueWidgetData) ───────────────────────
  const w1Data    = getData<{ issue_details: Parameters<typeof IssueDetailTable>[0]['details'] }>(w.w1)
  const w1Details = w1Data?.issue_details ?? []

  // ── 모달용 이슈 목록 ───────────────────────────────────────────
  const w2Data              = getData<{ issue_details: ReviewIssue[] }>(w.w2)
  const w3Data              = getData<{ issue_details: DataRequestIssue[] }>(w.w3)
  const w10Data             = getData<{ issue_details: ResultPendingIssue[] }>(w.w10)
  const reviewIssues        = w2Data?.issue_details  ?? []
  const dataRequestIssues   = w3Data?.issue_details  ?? []
  const resultPendingIssues = w10Data?.issue_details ?? []

  return (
    <div className="space-y-4 md:space-y-6 3xl:space-y-8">
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-7 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label={`${new Date().getFullYear()} 생성`} value={w.w5?.total ?? 0} color="gray" />
        <SummaryCard label={`${new Date().getFullYear()} 해결`} value={w.w6?.total ?? 0} color="gray" />
        <SummaryCard
          label="이번 주 생성"
          value={w11Created}
          color="blue"
          onClick={() => setShowWeeklyCreated(true)}
        />
        <SummaryCard
          label="이번 주 해결"
          value={w11Resolved}
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
          value={w.w10?.total ?? 0}
          color="yellow"
          onClick={() => setShowResultPending(true)}
        />
      </div>

      {/* 모달 */}
      {showWeeklyCreated && (
        <WeeklyCreatedModal
          issues={weeklyCreated}
          total={w11Created}
          onClose={() => setShowWeeklyCreated(false)}
        />
      )}
      {showWeeklyResolved && (
        <WeeklyResolvedModal
          issues={weeklyResolved}
          total={w11Resolved}
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
          total={w.w10?.total ?? 0}
          onClose={() => setShowResultPending(false)}
        />
      )}

      {/* 월별 SLA 달성률 */}
      {(hasW12 || hasW13) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
          <SlaMonthlyLineChart
            title="✅ 최초응답 SLA"
            subtitle="최근 6개월 · 응답시간 위반 여부"
            monthly={w12Monthly}
            color="#3b82f6"
          />
          <SlaMonthlyLineChart
            title="✅ 해결시간 SLA"
            subtitle="최근 6개월 · 해결시간 위반 여부"
            monthly={w13Monthly}
            color="#22c55e"
          />
        </div>
      )}

      {/* 차트 행 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 3xl:gap-5">
        <SlaDonutChart total={w9Total} distribution={w9Distribution} />
        <ReasonPieChart byStatus={w4ByStatus} />
        <div className="sm:col-span-2 md:col-span-1">
          <TrendLineChart created={w11Created} resolved={w11Resolved} />
        </div>
      </div>

      {/* 차트 행 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
        <TypeBarChart byType={w7ByType} />
        <ResolutionTimeChart details={recentIssues} />
      </div>

      <IssueDetailTable details={w1Details} />

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
