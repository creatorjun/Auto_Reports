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
import WeeklyCreatedModal, { type CreatedIssue } from '@/presentation/components/tables/WeeklyCreatedModal'
import WeeklyResolvedModal, { type ResolvedIssue } from '@/presentation/components/tables/WeeklyResolvedModal'
import IssueReviewModal, { type ReviewIssue } from '@/presentation/components/tables/IssueReviewModal'
import DataRequestModal, { type DataRequestIssue } from '@/presentation/components/tables/DataRequestModal'
import ResultPendingModal, { type ResultPendingIssue } from '@/presentation/components/tables/ResultPendingModal'
import IncompleteIssueModal, { type IncompleteIssue } from '@/presentation/components/tables/IncompleteIssueModal'
import type { ReportDetail } from '@/domain/Report'

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
  assignee?: string
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

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const w = report.widgets

  const w3Data = getData<{
    created: number
    resolved: number
    created_details: CreatedIssue[]
    resolved_details: ResolvedIssue[]
  }>(w.w3)
  const w3Created      = w3Data?.created          ?? 0
  const w3Resolved     = w3Data?.resolved         ?? 0
  const weeklyCreated  = w3Data?.created_details  ?? []
  const weeklyResolved = w3Data?.resolved_details ?? []

  const dateRange = report.week_start && report.week_end
    ? { start: report.week_start, end: report.week_end }
    : undefined

  const w7Data    = getData<{ monthly: MonthlyEntry[] }>(w.w7)
  const w8Data    = getData<{ monthly: MonthlyEntry[] }>(w.w8)
  const w7Monthly = w7Data?.monthly ?? []
  const w8Monthly = w8Data?.monthly ?? []
  const hasW7     = w7Monthly.some((e) => e.total > 0)
  const hasW8     = w8Monthly.some((e) => e.total > 0)

  const w9Data         = getData<W9Data>(w.w9)
  const w9Total        = w.w9?.total ?? 0
  const w9Distribution = w9Data?.violation_distribution ?? []

  const w10Data     = getData<{ by_status: Record<string, number> }>(w.w10)
  const w10ByStatus = w10Data?.by_status ?? {}

  const w11Data   = getData<{ by_type: Record<string, ResolutionTypeEntry> }>(w.w11)
  const w11ByType = w11Data?.by_type ?? {}

  const w12Data      = getData<{ issue_details: RecentIssue[] }>(w.w12)
  const recentIssues = w12Data?.issue_details ?? []

  const incompleteIssues: IncompleteIssue[] = recentIssues.map((i) => ({
    key:          i.key,
    summary:      i.summary,
    type:         i.type,
    status:       i.status,
    created:      i.created,
    elapsed_days: i.elapsed_days,
  }))
  const incompleteTotal = incompleteIssues.length

  const w4Data              = getData<{ issue_details: ReviewIssue[] }>(w.w4)
  const w5Data              = getData<{ issue_details: DataRequestIssue[] }>(w.w5)
  const w6Data              = getData<{ issue_details: ResultPendingIssue[] }>(w.w6)
  const reviewIssues        = w4Data?.issue_details ?? []
  const dataRequestIssues   = w5Data?.issue_details ?? []
  const resultPendingIssues = w6Data?.issue_details ?? []

  return (
    <div className="space-y-4 md:space-y-6 3xl:space-y-8">
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}

      <div className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-8 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label={`${new Date().getFullYear()} 생성`} value={w.w1?.total ?? 0} color="gray" />
        <SummaryCard label={`${new Date().getFullYear()} 해결`} value={w.w2?.total ?? 0} color="gray" />
        <SummaryCard
          label="생성"
          value={w3Created}
          color="blue"
          onClick={() => setShowWeeklyCreated(true)}
        />
        <SummaryCard
          label="완료"
          value={w3Resolved}
          color="green"
          onClick={() => setShowWeeklyResolved(true)}
        />
        <SummaryCard
          label="이슈 리뷰 중"
          value={w.w4?.total ?? 0}
          color="yellow"
          onClick={() => setShowIssueReview(true)}
        />
        <SummaryCard
          label="자료 요청 중"
          value={w.w5?.total ?? 0}
          color="yellow"
          onClick={() => setShowDataRequest(true)}
        />
        <SummaryCard
          label="결과 대기 중"
          value={w.w6?.total ?? 0}
          color="yellow"
          onClick={() => setShowResultPending(true)}
        />
        <SummaryCard
          label="미완료 이슈"
          value={incompleteTotal}
          color="red"
          onClick={() => setShowIncomplete(true)}
        />
      </div>

      {showWeeklyCreated  && <WeeklyCreatedModal  issues={weeklyCreated}       total={w3Created}        dateRange={dateRange} onClose={() => setShowWeeklyCreated(false)}  />}
      {showWeeklyResolved && <WeeklyResolvedModal issues={weeklyResolved}      total={w3Resolved}       dateRange={dateRange} onClose={() => setShowWeeklyResolved(false)} />}
      {showIssueReview    && <IssueReviewModal    issues={reviewIssues}        total={w.w4?.total ?? 0} onClose={() => setShowIssueReview(false)}    />}
      {showDataRequest    && <DataRequestModal    issues={dataRequestIssues}   total={w.w5?.total ?? 0} onClose={() => setShowDataRequest(false)}    />}
      {showResultPending  && <ResultPendingModal  issues={resultPendingIssues} total={w.w6?.total ?? 0} onClose={() => setShowResultPending(false)}  />}
      {showIncomplete     && <IncompleteIssueModal issues={incompleteIssues}   total={incompleteTotal}  onClose={() => setShowIncomplete(false)}     />}

      {(hasW7 || hasW8) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
          <SlaMonthlyLineChart
            title="✅ 최초응답 SLA"
            subtitle="최근 6개월 · 응답시간 위반 여부"
            monthly={w7Monthly}
            color="#3b82f6"
          />
          <SlaMonthlyLineChart
            title="✅ 해결시간 SLA"
            subtitle="최근 6개월 · 해결시간 위반 여부"
            monthly={w8Monthly}
            color="#22c55e"
          />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4 3xl:gap-5">
        <SlaDonutChart total={w9Total} distribution={w9Distribution} />
        <ReasonPieChart byStatus={w10ByStatus} />
        <TrendLineChart created={w3Created} resolved={w3Resolved} />
        <TypeBarChart byType={w11ByType} />
      </div>

      <ResolutionTimeChart details={recentIssues} />

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
      생성된 보고서가 없습니다. <span className="text-brand-600 font-medium">보고서 생성</span> 버튼을 누르세요.
    </div>
  )

  return <DashboardContent report={data} />
}
