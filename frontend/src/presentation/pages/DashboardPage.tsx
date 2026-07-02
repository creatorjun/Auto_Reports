import { useParams } from 'react-router-dom'
import { useLatestReport, useReportById } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SummaryCard from '@/presentation/components/cards/SummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import SlaDonutChart from '@/presentation/components/charts/SlaDonutChart'
import ReasonPieChart from '@/presentation/components/charts/ReasonPieChart'
import TypeBarChart from '@/presentation/components/charts/TypeBarChart'
import ResolutionTimeChart from '@/presentation/components/charts/ResolutionTimeChart'
import TrendLineChart from '@/presentation/components/charts/TrendLineChart'
import IssueDetailTable from '@/presentation/components/tables/IssueDetailTable'
import type { ReportDetail } from '@/domain/Report'

function DashboardContent({ report }: { report: ReportDetail }) {
  const w = report.widgets
  const w12 = w.w12?.breakdown as Record<string, number> ?? {}
  const w7  = w.w7?.breakdown  as Record<string, number> ?? {}
  const w10 = w.w10?.breakdown as Record<string, { avg_days: number; count: number }> ?? {}
  const w11 = w.w11?.breakdown as Record<string, unknown> ?? {}
  const w14 = w.w14?.breakdown as Record<string, number> ?? {}

  const details = (w11.issue_details ?? []) as Parameters<typeof IssueDetailTable>[0]['details']

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">TAC 주간 보고서</h1>
          <p className="text-sm text-gray-400 mt-0.5">{report.week_start} ~ {report.week_end} · 생성: {report.report_date}</p>
        </div>
      </div>

      {/* AI 종합 분석 */}
      {report.ai_analysis && <AiSummaryCard ai={report.ai_analysis} />}

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard icon="📝" label="이번 주 생성" value={w14['생성'] ?? 0} color="blue" />
        <SummaryCard icon="✅" label="이번 주 해결" value={w14['해결'] ?? 0} color="green" />
        <SummaryCard icon="⚠️" label="SLA 초과" value={w.w1?.total ?? 0} sub="30일 미해결" color="red" />
        <SummaryCard icon="🔴" label="개발 지연" value={w.w2?.total ?? 0} color="yellow" />
        <SummaryCard icon="📞" label="TAC & QA 지연" value={w.w3?.total ?? 0} color="yellow" />
        <SummaryCard icon="🤷" label="연구소 대기 미지정" value={w.w4?.total ?? 0} color="red" />
        <SummaryCard icon="📈" label="2026 생성" value={w.w8?.total ?? 0} color="gray" />
        <SummaryCard icon="📉" label="2026 해결" value={w.w9?.total ?? 0} color="gray" />
      </div>

      {/* 차트 1열 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SlaDonutChart met={w12['SLA 만족'] ?? 0} violated={w12['SLA 위반'] ?? 0} />
        <ReasonPieChart breakdown={w7} />
        <TrendLineChart created={w14['생성'] ?? 0} resolved={w14['해결'] ?? 0} />
      </div>

      {/* 차트 2열 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TypeBarChart breakdown={w10} />
        <ResolutionTimeChart details={details} />
      </div>

      {/* 해결 이슈 테이블 */}
      <IssueDetailTable details={details} />
    </div>
  )
}

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>()
  const latestQuery = useLatestReport()
  const byIdQuery  = useReportById(Number(id))

  const { data, isLoading, error } = id ? byIdQuery : latestQuery

  if (isLoading) return <LoadingSpinner text="보고서 로딩 중..." />
  if (error)     return <div className="card text-red-500">❌ 데이터를 불러올 수 없습니다.</div>
  if (!data)     return <div className="card text-gray-400 text-center py-12">생성된 보고서가 없습니다. "보고서 지금 생성" 버튼을 누르세요.</div>

  return <DashboardContent report={data} />
}
