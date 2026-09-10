// frontend/.palette-preview/main.tsx
import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import SummaryCard, { SUMMARY_ICONS } from '@/presentation/components/cards/SummaryCard'
import WorkTypeSummaryCard from '@/presentation/components/cards/WorkTypeSummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import AnnualSummaryMetrics from '@/presentation/components/annual/AnnualSummaryMetrics'
import AnnualMonthlyComparison from '@/presentation/components/annual/AnnualMonthlyComparison'
import RedeploymentAnnualSection from '@/presentation/components/annual/RedeploymentAnnualSection'
import SlaDonutChart from '@/presentation/components/charts/SlaDonutChart'
import ReasonPieChart from '@/presentation/components/charts/ReasonPieChart'
import TrendLineChart from '@/presentation/components/charts/TrendLineChart'
import TypeBarChart from '@/presentation/components/charts/TypeBarChart'
import MonthlyCountChart from '@/presentation/components/charts/MonthlyCountChart'
import SlaMonthlyLineChart from '@/presentation/components/charts/SlaMonthlyLineChart'
import { DashboardExportProvider } from '@/presentation/context/DashboardExportContext'
import { MONTHLY_COUNT_COLORS, SLA_MONTHLY_COLORS } from '@/presentation/config/constants'
import type { RedeploymentAnalytics } from '@/domain/Dashboard'
import '@/presentation/styles/palette.css'
import '@/presentation/styles/index.css'
import '@/presentation/styles/annualReport.css'
import '@/presentation/styles/dashboardExport.css'

document.documentElement.dataset.theme = 'dark'

const created = [74, 68, 90, 105, 81, 112, 97, 95, 16].map((count, index) => ({ month: `2026-${String(index + 1).padStart(2, '0')}`, year: 2026, month_num: index + 1, count }))
const resolved = created.map((entry, index) => ({ ...entry, count: [68, 75, 82, 101, 96, 108, 103, 98, 29][index] }))
const slaMonthly = created.map((entry, index) => ({ month: entry.month, year: entry.year, month_num: entry.month_num, total: 100, met: [94, 91, 86, 96, 92, 97, 94, 96, 90][index], rate: [94, 91, 86, 96, 92, 97, 94, 96, 90][index] }))
const statuses = { '결과 대기 중': 23, '연구소 검토 중': 8, '자료 요청 중': 6, '이슈 리뷰 중': 5, '배포 파일 검토 중': 4, '연구소 대기 중': 3, '처리 중': 2, '구현 중': 1, '재오픈': 1 }
const violation = [
  { stage: '최초 응답 SLA', count: 4, rate: 4 },
  { stage: '해결 시간 SLA', count: 94, rate: 94 },
  { stage: '둘 다 위반', count: 2, rate: 2 },
]
const resolution = Object.fromEntries([['CVE', 26], ['개선', 57], ['인시던트', 43], ['서비스 요청', 27], ['H/W 장애 요청', 27]].map(([name, days]) => [name, { avg_days: Number(days), avg_hours: Number(days) * 24, count: 10 }]))
const types = ['개선', '인시던트', '서비스 요청', 'CVE', 'H/W 장애 요청', '기술 지원']
const redeployment: RedeploymentAnalytics = {
  resolved_total: 760,
  redeployment_total: 60,
  redeployment_rate: 7.9,
  analytics_total: 60,
  classification_complete: true,
  monthly: created.map((entry, index) => ({ month: entry.month, year: entry.year, month_num: entry.month_num, total: 6 + index, by_type: Object.fromEntries(types.map((type, typeIndex) => [type, (index + typeIndex) % 4 + 1])) })),
  by_cause: { '기능 개선': 22, '설정 변경': 14, '오류 수정': 10, '보안 패치': 7, '환경 변경': 5, '추가 요청': 2 },
  by_assignee: { '검증 담당 A': 20, '검증 담당 B': 16, '검증 담당 C': 12, '검증 담당 D': 7, '검증 담당 E': 5 },
  partner_matrix: { '검증 파트너 A': { '개선': 10, '인시던트': 5, '서비스 요청': 2 }, '검증 파트너 B': { '개선': 3, '인시던트': 7, '서비스 요청': 1 }, '검증 파트너 C': { '개선': 1, '인시던트': 2, '서비스 요청': 9 } },
  latest_issues: Array.from({ length: 7 }, (_, index) => ({ key: `PALETTE-${index + 1}`, summary: `색상 확인용 가상 이슈 ${index + 1}`, type: types[index % types.length], priority: '보통', resolved: '2026-09-01', month: '2026-09', cause: '설정 변경', assignee: '검증 담당자', partners: ['검증 파트너 A'] })),
  source_jqls: {},
}

function App() {
  const [theme, setTheme] = useState('dark')
  const [annual, setAnnual] = useState(true)
  const [showPrint, setShowPrint] = useState(false)
  const [clicked, setClicked] = useState('')
  const selectTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    setTheme(next)
  }
  const wrapper = annual ? 'dashboard-view annual-report-view space-y-6' : 'dashboard-view space-y-6'
  return (
    <main style={{ maxWidth: 1728, margin: '0 auto', padding: 24 }}>
      <header className="card" style={{ marginBottom: 20, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16 }}>
        <strong>실제 컴포넌트 · 가상 데이터 색상 검증</strong>
        <button className="bg-apple-gray text-apple-dark rounded-lg px-4 py-2" onClick={selectTheme}>{theme === 'dark' ? '라이트 모드' : '다크 모드'}</button>
        <button className="bg-apple-gray text-apple-dark rounded-lg px-4 py-2" onClick={() => setAnnual(!annual)}>{annual ? '대시보드 보기' : '연간 보고서 보기'}</button>
        <button className="bg-apple-gray text-apple-dark rounded-lg px-4 py-2" onClick={() => setShowPrint(!showPrint)}>인쇄 색상 {showPrint ? '숨기기' : '보기'}</button>
        <span role="status" style={{ fontSize: 13 }}>{clicked}</span>
      </header>
      <div className={wrapper}>
        <section data-pdf-section="분석 차트" className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SlaDonutChart total={100} distribution={violation} onSliceClick={(entry) => setClicked(`${entry.stage} 클릭 확인`)} />
          <ReasonPieChart byStatus={statuses} onSliceClick={(status) => setClicked(`${status} 클릭 확인`)} />
          <TrendLineChart created={738} resolved={760} periodLabel="2026년 전체" onBarClick={(key) => setClicked(`${key} 클릭 확인`)} />
          <TypeBarChart byType={resolution} />
        </section>
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard label="기간 내 생성" value={738} color="blue" icon={SUMMARY_ICONS.weekCreated} onClick={() => setClicked('생성 카드 클릭 확인')} />
          <SummaryCard label="기간 내 해결" value={760} color="green" icon={SUMMARY_ICONS.weekResolved} onClick={() => setClicked('해결 카드 클릭 확인')} />
          <SummaryCard label="결과 대기 중" value={23} color="yellow" icon={SUMMARY_ICONS.resultPending} onClick={() => setClicked('대기 카드 클릭 확인')} />
          <SummaryCard label="미완료 이슈" value={97} color="red" icon={SUMMARY_ICONS.incomplete} onClick={() => setClicked('미완료 카드 클릭 확인')} />
        </section>
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <WorkTypeSummaryCard label="인시던트" count={15} onClick={() => setClicked('열린 요청 클릭 확인')} />
          <WorkTypeSummaryCard label="서비스 요청" count={42} onClick={() => setClicked('열린 요청 클릭 확인')} />
        </section>
        <AnnualSummaryMetrics period="2026년 전체" created={738} resolved={760} createdDetails={738} resolvedDetails={760} onCreated={() => setClicked('연간 생성 클릭 확인')} onResolved={() => setClicked('연간 해결 클릭 확인')} statuses={Object.entries(statuses).slice(0, 4).map(([label, value]) => ({ label, value, onClick: () => setClicked(`${label} 클릭 확인`) }))} />
        <AiSummaryCard ai={{ sentiment: 'warning', summary: '색상과 가독성 검증을 위한 가상 분석입니다.', risks: ['처리 지연 항목의 추이를 확인합니다.'], recommendations: ['담당자와 후속 조치 일정을 확인합니다.'] }} />
        <AnnualMonthlyComparison created={created} resolved={resolved} year={2026} periodEnd="2026-09-09" subtitle="2026년 전체" />
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MonthlyCountChart title="월별 등록 건수" subtitle="2026년 전체" monthly={created} color={MONTHLY_COUNT_COLORS.created} />
          <MonthlyCountChart title="월별 해결 건수" subtitle="2026년 전체" monthly={resolved} color={MONTHLY_COUNT_COLORS.resolved} />
          <SlaMonthlyLineChart title="최초응답 SLA" subtitle="2026년 전체" monthly={slaMonthly} color={SLA_MONTHLY_COLORS.initial} />
          <SlaMonthlyLineChart title="해결시간 SLA" subtitle="2026년 전체" monthly={slaMonthly} color={SLA_MONTHLY_COLORS.resolution} />
        </section>
        <RedeploymentAnnualSection data={redeployment} year={2026} />
      </div>
      <div className="dashboard-pdf-stage" data-palette-print-probe="" style={showPrint ? { position: 'relative', left: 0, width: '100%', marginTop: 24, pointerEvents: 'auto' } : undefined}>
        <DashboardExportProvider>
          <div className="dashboard-view annual-report-view" style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            <h2 style={{ width: '100%' }}>PDF 팔레트 확인</h2>
            <TrendLineChart created={738} resolved={760} periodLabel="2026년 전체" />
            <SlaDonutChart total={100} distribution={violation} />
          </div>
        </DashboardExportProvider>
      </div>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
