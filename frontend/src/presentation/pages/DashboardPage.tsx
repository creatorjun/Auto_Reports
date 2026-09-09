// frontend/src/presentation/pages/DashboardPage.tsx
import { lazy, Suspense, useCallback, useEffect, useState, useMemo, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { BarChart2, ShieldAlert, Activity, Pin, CalendarRange, RefreshCw, Download } from 'lucide-react'
import { useAnnualReport, useLatestReport, useReportById } from '@/presentation/hooks/useReport'
import { useReportStore } from '@/presentation/state/reportStore'
import { useDashboardData } from '@/presentation/hooks/useDashboardData'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SummaryCard, { SUMMARY_ICONS } from '@/presentation/components/cards/SummaryCard'
import AiSummaryCard from '@/presentation/components/cards/AiSummaryCard'
import WorkTypeSummaryCard from '@/presentation/components/cards/WorkTypeSummaryCard'
import SectionTitle from '@/presentation/components/common/SectionTitle'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import { ModalFallback, ChartFallback } from '@/presentation/components/common/DashboardFallbacks'
import { MONTHLY_COUNT_COLORS, SLA_MONTHLY_COLORS } from '@/presentation/config/constants'
import type { ReportDetail } from '@/domain/Report'
import type { DashboardPdfDocument } from '@/domain/DashboardExport'
import DashboardPdfExportStage from '@/presentation/components/export/DashboardPdfExportStage'
import '@/presentation/styles/dashboardExport.css'
import type { RedeploymentAnalytics, Semester, SlaDelayIssue, ViolationEntry, WorkTypeOpenWidget } from '@/domain/Dashboard'
import type { SlaViolationIssue } from '@/presentation/components/tables/SlaViolationModal'
import AnnualReportHeader from '@/presentation/components/annual/AnnualReportHeader'
import AnnualYearComparison from '@/presentation/components/annual/AnnualYearComparison'
import AnnualSummaryMetrics from '@/presentation/components/annual/AnnualSummaryMetrics'
import '@/presentation/styles/annualReport.css'
import { WIDGET_ID } from '@/domain/WidgetId'

const SlaDonutChart       = lazy(() => import('@/presentation/components/charts/SlaDonutChart'))
const ReasonPieChart      = lazy(() => import('@/presentation/components/charts/ReasonPieChart'))
const TypeBarChart        = lazy(() => import('@/presentation/components/charts/TypeBarChart'))
const ResolutionTimeChart = lazy(() => import('@/presentation/components/charts/ResolutionTimeChart'))
const TrendLineChart      = lazy(() => import('@/presentation/components/charts/TrendLineChart'))
const SlaMonthlyLineChart = lazy(() => import('@/presentation/components/charts/SlaMonthlyLineChart'))
const MonthlyCountChart   = lazy(() => import('@/presentation/components/charts/MonthlyCountChart'))
const RedeploymentAnnualSection = lazy(() => import('@/presentation/components/annual/RedeploymentAnnualSection'))
const AnnualMonthlyComparison = lazy(() => import('@/presentation/components/annual/AnnualMonthlyComparison'))

const WeeklyCreatedModal  = lazy(() => import('@/presentation/components/tables/WeeklyCreatedModal'))
const WeeklyResolvedModal = lazy(() => import('@/presentation/components/tables/WeeklyResolvedModal'))
const IssueReviewModal    = lazy(() => import('@/presentation/components/tables/IssueReviewModal'))
const DataRequestModal    = lazy(() => import('@/presentation/components/tables/DataRequestModal'))
const ResultPendingModal  = lazy(() => import('@/presentation/components/tables/ResultPendingModal'))
const IncompleteIssueModal = lazy(() => import('@/presentation/components/tables/IncompleteIssueModal'))
const SlaViolationModal   = lazy(() => import('@/presentation/components/tables/SlaViolationModal'))
const SlaDelayModal       = lazy(() => import('@/presentation/components/tables/SlaDelayModal'))

const WORK_TYPE_TONES = ['blue', 'green', 'red', 'yellow', 'purple'] as const

interface ExportSelection {
  selectedIssueTypes: Set<string> | null
  selectedSemester: Semester | null
}

interface ExportSnapshot {
  report: ReportDetail
  selection: ExportSelection
  metadata: Omit<DashboardPdfDocument, 'sections'>
  fileName: string
}

function DashboardContent({ report, exportSelection }: { report: ReportDetail; exportSelection?: ExportSelection }) {
  const isAnnual = report.scope === 'annual'
  const { setCurrentReport } = useReportStore()
  const [selectedIssueTypes, setSelectedIssueTypes] = useState<Set<string> | null>(null)
  const [selectedSemester,   setSelectedSemester]   = useState<Semester | null>(null)
  const [showWeeklyCreated,  setShowWeeklyCreated]  = useState(false)
  const [showWeeklyResolved, setShowWeeklyResolved] = useState(false)
  const [workTypeOpen,       setWorkTypeOpen]       = useState<WorkTypeOpenWidget | null>(null)
  const [showIssueReview,    setShowIssueReview]    = useState(false)
  const [showDataRequest,    setShowDataRequest]    = useState(false)
  const [showResultPending,  setShowResultPending]  = useState(false)
  const [showIncomplete,     setShowIncomplete]     = useState(false)
  const [slaViolationEntry,  setSlaViolationEntry]  = useState<ViolationEntry | null>(null)
  const [slaDelayEntry,      setSlaDelayEntry]      = useState<{ status: string; issues: SlaDelayIssue[] } | null>(null)
  const [exportSnapshot, setExportSnapshot] = useState<ExportSnapshot | null>(null)
  const [exportError, setExportError] = useState('')
  const exportPending = useRef(false)
  const effectiveIssueTypes = exportSelection ? exportSelection.selectedIssueTypes : selectedIssueTypes
  const effectiveSemester = exportSelection ? exportSelection.selectedSemester : selectedSemester

  useEffect(() => {
    if (exportSelection) return
    setSelectedIssueTypes(null)
    setSelectedSemester(null)
    setCurrentReport(report)
    return () => setCurrentReport(null)
  }, [exportSelection, report, setCurrentReport])

  const { filter, yearly, weekly, workTypeOpen: workTypeOpenWidgets, slaMonthly, monthlyCount, slaDonut, slaDelay, resolutionByType, recentAndIncomplete, statusIssues } = useDashboardData(report, effectiveIssueTypes, effectiveSemester)
  const { issueTypes, reportYear, supportsIssueTypeFiltering, supportsSemesterFiltering, semesterLabel } = filter
  const { w1YearlyCreated, w2YearlyResolved } = yearly
  const { w3Created, w3Resolved, weeklyCreated, weeklyResolved, dateRange, rangeDays } = weekly
  const { w10Monthly, w11Monthly, hasW10, hasW11 } = slaMonthly
  const { w8Monthly, w9Monthly, hasW8, hasW9 } = monthlyCount
  const { w12Total, w12Distribution } = slaDonut
  const { w13ByStatus, w13ByStatusDetails } = slaDelay
  const { recentIssues, incompleteIssues, incompleteTotal } = recentAndIncomplete
  const { reviewIssues, dataRequestIssues, resultPendingIssues, reviewTotal, dataRequestTotal, resultPendingTotal } = statusIssues
  const redeploymentData = report.scope === 'annual'
    ? report.widgets[WIDGET_ID.REDEPLOYMENT_ANALYTICS]?.data as unknown as RedeploymentAnalytics | null
    : null

  const slaModalIssues: SlaViolationIssue[] = useMemo(() => {
    if (!slaViolationEntry) return []
    return (slaViolationEntry.issue_details ?? []) as SlaViolationIssue[]
  }, [slaViolationEntry])

  const handleTrendBarClick = (key: '생성' | '해결') => {
    if (key === '생성') setShowWeeklyCreated(true)
    else setShowWeeklyResolved(true)
  }

  const handleIssueTypeToggle = (issueType: string) => {
    setSelectedIssueTypes((current) => {
      const next = new Set(current ?? issueTypes)
      if (next.has(issueType)) next.delete(issueType)
      else next.add(issueType)
      return next.size === issueTypes.length ? null : next
    })
  }

  const finishExport = useCallback(() => {
    exportPending.current = false
    setExportSnapshot(null)
  }, [])

  const failExport = useCallback((message: string) => {
    setExportError(message)
    finishExport()
  }, [finishExport])

  const startExport = () => {
    if (exportPending.current) return
    exportPending.current = true
    setExportError('')
    const title = report.scope === 'annual' ? `${report.report_year} 연간 보고서` : 'TAC 대시보드'
    const filters = [
      effectiveSemester === 'h1' ? '상반기' : effectiveSemester === 'h2' ? '하반기' : '전체 기간',
      effectiveIssueTypes === null ? '전체 업무 유형' : effectiveIssueTypes.size ? [...effectiveIssueTypes].join(', ') : '선택된 업무 유형 없음',
    ]
    if (redeploymentData && (effectiveSemester !== null || effectiveIssueTypes !== null)) {
      filters.push('재배포 품질 지표는 연간 전체 기준')
    }
    setExportSnapshot({
      report,
      selection: {
        selectedIssueTypes: effectiveIssueTypes === null ? null : new Set(effectiveIssueTypes),
        selectedSemester: effectiveSemester,
      },
      metadata: {
        title,
        period: `${report.week_start} ~ ${report.week_end}`,
        generatedAt: new Date().toLocaleString('ko-KR', { hour12: false }),
        filters,
      },
      fileName: `${title.replace(/\s+/g, '_')}_${report.week_start}_${report.week_end}.pdf`,
    })
  }

  const exportActions = !exportSelection && (
        <div className="flex flex-wrap items-center justify-end gap-3">
          <span className="text-[12px] text-apple-mid">{isAnnual ? '선택 연도 · 현재 필터' : '현재 필터 · 표 전체 포함'}</span>
          <button
            type="button"
            onClick={startExport}
            disabled={exportSnapshot !== null}
            aria-busy={exportSnapshot !== null}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-wait disabled:opacity-60"
          >
            {exportSnapshot ? <RefreshCw size={16} className="animate-spin" /> : <Download size={16} />}
            <span aria-live="polite">{exportSnapshot ? 'PDF 생성 중...' : 'PDF 내보내기'}</span>
          </button>
          {exportError && <p role="alert" className="w-full text-right text-[13px] text-red-600">{exportError}</p>}
        </div>
      )

  return (
    <>
    <div className={`${isAnnual ? 'dashboard-report-view annual-report-view space-y-6 md:space-y-8' : 'dashboard-report-view space-y-4 md:space-y-6 3xl:space-y-8'}${exportSelection ? ' dashboard-report-export-view' : ''}`}>
      {isAnnual ? <AnnualReportHeader report={report} actions={exportActions} /> : exportActions}
      {isAnnual && !exportSelection && <AnnualYearComparison report={report} />}
      {!exportSelection && <IssueTypeFilter
        issueTypes={issueTypes}
        selectedTypes={selectedIssueTypes}
        selectedSemester={selectedSemester}
        supported={supportsIssueTypeFiltering}
        semesterSupported={supportsSemesterFiltering}
        onToggle={handleIssueTypeToggle}
        onSemesterChange={setSelectedSemester}
        onReset={() => {
          setSelectedIssueTypes(null)
          setSelectedSemester(null)
        }}
      />}
      {!isAnnual && report.ai_analysis && effectiveIssueTypes === null && effectiveSemester === null && <div data-pdf-section="AI 종합 분석"><AiSummaryCard ai={report.ai_analysis} /></div>}
      {isAnnual ? (
        <AnnualSummaryMetrics
          period={semesterLabel}
          created={w1YearlyCreated}
          resolved={w2YearlyResolved}
          createdDetails={w3Created}
          resolvedDetails={w3Resolved}
          onCreated={() => setShowWeeklyCreated(true)}
          onResolved={() => setShowWeeklyResolved(true)}
          statuses={[
            { label: '이슈 리뷰 중', value: reviewTotal, tone: 'purple', onClick: () => setShowIssueReview(true) },
            { label: '자료 요청 중', value: dataRequestTotal, tone: 'blue', onClick: () => setShowDataRequest(true) },
            { label: '결과 대기 중', value: resultPendingTotal, tone: 'yellow', onClick: () => setShowResultPending(true) },
            { label: '미완료 이슈', value: incompleteTotal, tone: 'red', onClick: () => setShowIncomplete(true) },
          ]}
        />
      ) : <div data-pdf-section="주요 지표" data-pdf-kind="metrics" className="grid grid-cols-2 md:grid-cols-4 3xl:grid-cols-8 gap-3 md:gap-4 3xl:gap-5">
        <SummaryCard label={`${reportYear} 생성`} value={w1YearlyCreated} color="blue"   icon={SUMMARY_ICONS.yearCreated}   />
        <SummaryCard label={`${reportYear} 해결`} value={w2YearlyResolved} color="green"  icon={SUMMARY_ICONS.yearResolved}   />
        <SummaryCard label={`${rangeDays}일 생성`} value={w3Created}  color="blue"  icon={SUMMARY_ICONS.weekCreated}  onClick={() => setShowWeeklyCreated(true)}  />
        <SummaryCard label={`${rangeDays}일 완료`} value={w3Resolved} color="green" icon={SUMMARY_ICONS.weekResolved} onClick={() => setShowWeeklyResolved(true)} />
        <SummaryCard label="이슈 리뷰 중" value={reviewTotal}  color="purple" icon={SUMMARY_ICONS.issueReview}   onClick={() => setShowIssueReview(true)}   />
        <SummaryCard label="자료 요청 중" value={dataRequestTotal}  color="blue" icon={SUMMARY_ICONS.dataRequest}   onClick={() => setShowDataRequest(true)}   />
        <SummaryCard label="결과 대기 중" value={resultPendingTotal}  color="yellow" icon={SUMMARY_ICONS.resultPending} onClick={() => setShowResultPending(true)} />
        <SummaryCard label="미완료 이슈"  value={incompleteTotal}   color="red"    icon={SUMMARY_ICONS.incomplete}    onClick={() => setShowIncomplete(true)}    />
      </div>}
      {isAnnual && report.ai_analysis && effectiveIssueTypes === null && effectiveSemester === null && <div data-pdf-section="AI 종합 분석"><AiSummaryCard ai={report.ai_analysis} /></div>}

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
      {workTypeOpen && (
        <Suspense fallback={<ModalFallback />}>
          <IncompleteIssueModal
            title={`${workTypeOpen.label} 열린 요청`}
            issues={workTypeOpen.issues}
            total={workTypeOpen.count}
            onClose={() => setWorkTypeOpen(null)}
          />
        </Suspense>
      )}
      {showIssueReview && (
        <Suspense fallback={<ModalFallback />}>
          <IssueReviewModal issues={reviewIssues} total={reviewTotal} onClose={() => setShowIssueReview(false)} />
        </Suspense>
      )}
      {showDataRequest && (
        <Suspense fallback={<ModalFallback />}>
          <DataRequestModal issues={dataRequestIssues} total={dataRequestTotal} onClose={() => setShowDataRequest(false)} />
        </Suspense>
      )}
      {showResultPending && (
        <Suspense fallback={<ModalFallback />}>
          <ResultPendingModal issues={resultPendingIssues} total={resultPendingTotal} onClose={() => setShowResultPending(false)} />
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

      <div data-pdf-section="업무 유형별 열린 요청" data-pdf-kind="metrics" className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3 md:gap-4 3xl:gap-5">
        {isAnnual && <h2 className="col-span-full text-lg font-semibold text-apple-dark">업무 유형별 열린 요청</h2>}
        {workTypeOpenWidgets.map((widget, index) => (
          <WorkTypeSummaryCard
            key={widget.key}
            label={widget.label}
            count={widget.count}
            tone={WORK_TYPE_TONES[index % WORK_TYPE_TONES.length]}
            onClick={() => setWorkTypeOpen(widget)}
          />
        ))}
      </div>

      {(isAnnual ? w8Monthly.length > 0 || w9Monthly.length > 0 : hasW8 || hasW9) && (
        <div data-pdf-section="월별 이슈 현황" className="space-y-1">
          <SectionTitle icon={BarChart2} title="월별 이슈 현황" subtitle={semesterLabel} />
          {isAnnual ? (
            <Suspense fallback={<ChartFallback />}>
              <AnnualMonthlyComparison created={w8Monthly} resolved={w9Monthly} year={reportYear} periodEnd={report.week_end} subtitle={semesterLabel} />
            </Suspense>
          ) : <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5">
            <Suspense fallback={<ChartFallback />}>
              <MonthlyCountChart title="월별 등록 건수" subtitle={semesterLabel} monthly={w8Monthly} color={MONTHLY_COUNT_COLORS.created}  />
            </Suspense>
            <Suspense fallback={<ChartFallback />}>
              <MonthlyCountChart title="월별 해결 건수" subtitle={semesterLabel} monthly={w9Monthly} color={MONTHLY_COUNT_COLORS.resolved} />
            </Suspense>
          </div>}
        </div>
      )}
      {(hasW10 || hasW11) && (
        <div data-pdf-section="SLA 준수율" className="space-y-1">
          <SectionTitle icon={ShieldAlert} title="SLA 준수율" subtitle={semesterLabel} />
          <div className={isAnnual ? 'grid grid-cols-1 xl:grid-cols-2 gap-4' : 'grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 3xl:gap-5'}>
            <Suspense fallback={<ChartFallback />}>
              <SlaMonthlyLineChart title="최초응답 SLA" subtitle={`${semesterLabel} · 응답시간 위반 여부`} monthly={w10Monthly} color={SLA_MONTHLY_COLORS.initial}    />
            </Suspense>
            <Suspense fallback={<ChartFallback />}>
              <SlaMonthlyLineChart title="해결시간 SLA" subtitle={`${semesterLabel} · 해결시간 위반 여부`} monthly={w11Monthly} color={SLA_MONTHLY_COLORS.resolution} />
            </Suspense>
          </div>
        </div>
      )}
      <div data-pdf-section="분석 차트" className="space-y-1">
        <SectionTitle icon={Activity} title="분석 차트" />
        <div className={isAnnual ? 'grid grid-cols-1 lg:grid-cols-2 gap-4' : 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4 3xl:gap-5'}>
          <Suspense fallback={<ChartFallback />}>
            <SlaDonutChart
              total={w12Total}
              distribution={w12Distribution}
              onSliceClick={(entry) => setSlaViolationEntry(entry)}
            />
          </Suspense>
          <Suspense fallback={<ChartFallback />}>
            <ReasonPieChart
              byStatus={w13ByStatus}
              byStatusDetails={w13ByStatusDetails}
              onSliceClick={(status, issues) => setSlaDelayEntry({ status, issues })}
            />
          </Suspense>
          <Suspense fallback={<ChartFallback />}>
            <TrendLineChart
              created={w3Created}
              resolved={w3Resolved}
              periodLabel={isAnnual ? semesterLabel : undefined}
              onBarClick={handleTrendBarClick}
            />
          </Suspense>
          <Suspense fallback={<ChartFallback />}>
            <TypeBarChart byType={resolutionByType} />
          </Suspense>
        </div>
      </div>
      {redeploymentData && report.report_year != null && (
        <Suspense fallback={<ChartFallback />}>
          <RedeploymentAnnualSection data={redeploymentData} year={report.report_year} />
        </Suspense>
      )}
      <div data-pdf-section="최근 이슈 현황" className="space-y-1">
        <SectionTitle icon={Pin} title="최근 이슈 현황" subtitle={`최신 ${recentIssues.length}건`} />
        <Suspense fallback={<ChartFallback />}>
          <ResolutionTimeChart details={recentIssues} />
        </Suspense>
      </div>
    </div>
    {exportSnapshot && !exportSelection && (
      <DashboardPdfExportStage
        metadata={exportSnapshot.metadata}
        fileName={exportSnapshot.fileName}
        onComplete={finishExport}
        onError={failExport}
      >
        <DashboardContent report={exportSnapshot.report} exportSelection={exportSnapshot.selection} />
      </DashboardPdfExportStage>
    )}
    </>
  )
}

export default function DashboardPage() {
  const { id, year } = useParams<{ id: string; year: string }>()
  const annualYear = Number(year)
  const latestQuery = useLatestReport()
  const byIdQuery   = useReportById(Number(id))
  const annualQuery = useAnnualReport(annualYear)
  const { data, isLoading, error } = year ? annualQuery : id ? byIdQuery : latestQuery

  if (isLoading) return <LoadingSpinner text="보고서 로딩 중..." />
  if (error && year) return (
    <div className="card text-center py-16">
      <CalendarRange className="mx-auto mb-3 text-apple-light" size={28} />
      <p className="text-ui-base font-medium text-apple-dark">{annualYear} 연간 보고서가 아직 생성되지 않았습니다.</p>
      <p className="mt-2 text-[12px] text-apple-light">
        {annualYear === 2026
          ? '2026-01-01부터 오늘까지의 기간으로 보고서를 생성하면 자동으로 연결됩니다.'
          : `${annualYear}-01-01부터 ${annualYear}-12-31까지의 기간으로 보고서를 생성하면 자동으로 연결됩니다.`}
      </p>
    </div>
  )
  if (error) return <div className="card text-ui-base text-red-500">데이터를 불러올 수 없습니다.</div>
  if (!data)     return (
    <div className="card text-ui-base text-apple-light text-center py-16">
      생성된 보고서가 없습니다. <span className="text-brand-600 font-medium">보고서 생성</span> 버튼을 누르세요.
    </div>
  )
  return <DashboardContent report={data} />
}
