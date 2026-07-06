// frontend/src/presentation/pages/DashboardPage.tsx
import { useEffect } from 'react'
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
import IssueDetailTable from '@/presentation/components/tables/IssueDetailTable'
import SlaRateCard from '@/presentation/components/cards/SlaRateCard'
import type { ReportDetail } from '@/domain/Report'

interface SlaBreakdown {
  rate: number
  met: number
  total: number
  threshold_hours?: number
  threshold_days?: number
}

function DashboardContent({ report }: { report: ReportDetail }) {
  const { setCurrentReport } = useReportStore()

  useEffect(() => {
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [report, setCurrentReport])

  const w    = report.widgets
  const w12  = w.w12?.breakdown as Record<string, number> ?? {}
  const w7   = w.w7?.breakdown  as Record<string, number> ?? {}
  const w10  = w.w10?.breakdown as Record<string, { avg_days: number; count: number }> ?? {}
  const w11  = w.w11?.breakdown as Record<string, unknown> ?? {}
  const w14  = w.w14?.breakdown as Record<string, number> ?? {}
  const w15  = (w.w15?.breakdown ?? {}) as SlaBreakdown
  const w16  = (w.w16?.breakdown ?? {}) as SlaBreakdown
  const details = (w11.issue_details ?? []) as Parameters<typeof IssueDetailTable>[0]['details']

  return (
    <div className="space-y-4 md:space-y-6 3xl:space-y-8">
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-8 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label="이번 주 생성"       value={w14['생성'] ?? 0}  color="blue"   />
        <SummaryCard label="이번 주 해결"       value={w14['해결'] ?? 0}  color="green"  />
        <SummaryCard label="SLA 초과"           value={w.w1?.total ?? 0} sub="30일 미해결" color="red"    />
        <SummaryCard label="개발 지연"         value={w.w2?.total ?? 0} color="yellow" />
        <SummaryCard label="TAC & QA 지연"    value={w.w3?.total ?? 0} color="yellow" />
        <SummaryCard label="연구소 대기 미지정" value={w.w4?.total ?? 0} color="red"    />
        <SummaryCard label="2026 생성"          value={w.w8?.total ?? 0} color="gray"   />
        <SummaryCard label="2026 해결"          value={w.w9?.total ?? 0} color="gray"   />
      </div>

      {/* 월별 SLA 준수율 */}
      {(w15.total > 0 || w16.total > 0) && (
        <div>
          <h2 className="text-[13px] md:text-[14px] font-semibold text-apple-dark mb-3">
            월별 SLA 준수율
            <span className="ml-2 text-[11px] font-normal text-apple-light">최근 30일 기준</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
            {w15.total > 0 && (
              <SlaRateCard
                label="초기 대응 SLA"
                rate={w15.rate ?? 0}
                met={w15.met ?? 0}
                total={w15.total ?? 0}
                thresholdLabel={`${w15.threshold_hours ?? 24}시간 이내 리뷰 전환`}
              />
            )}
            {w16.total > 0 && (
              <SlaRateCard
                label="해결시간 SLA"
                rate={w16.rate ?? 0}
                met={w16.met ?? 0}
                total={w16.total ?? 0}
                thresholdLabel={`${w16.threshold_days ?? 30}일 이내 해결`}
              />
            )}
          </div>
        </div>
      )}

      {/* 차트 행 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 3xl:gap-5">
        <SlaDonutChart met={w12['SLA 만족'] ?? 0} violated={w12['SLA 위반'] ?? 0} />
        <ReasonPieChart breakdown={w7} />
        <div className="sm:col-span-2 md:col-span-1">
          <TrendLineChart created={w14['생성'] ?? 0} resolved={w14['해결'] ?? 0} />
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
      생성된 보고서가 없습니다. <span className="text-brand-600 font-medium">보고서 생성</span> 버튼을 눌러주세요.
    </div>
  )

  return <DashboardContent report={data} />
}
