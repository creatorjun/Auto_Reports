// frontend/src/presentation/pages/CLevelReportPage.tsx
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { CalendarDays, Download, History, RefreshCw, Save } from 'lucide-react'
import type { CLevelPeriod, CLevelViolation } from '@/domain/CLevelReport'
import { cLevelDate, cLevelToday } from '@/application/services/cLevelReport'
import { buildCLevelExport, type CLevelExportSelection } from '@/application/services/cLevelExport'
import { useCLevelReport } from '@/presentation/hooks/useCLevelReport'
import { useCLevelExport } from '@/presentation/hooks/useCLevelExport'
import { useReportStore } from '@/presentation/state/reportStore'
import CLevelOverview from '@/presentation/components/clevel/CLevelOverview'
import CLevelIssueDetail from '@/presentation/components/clevel/CLevelIssueDetail'
import { cLevelError } from '@/presentation/components/clevel/CLevelShared'
import '@/presentation/styles/cLevelReport.css'

const INITIAL_SELECTION: CLevelExportSelection = { minimumMonths: 1, trendType: 'all', violationMetric: 'all', violationType: 'all' }

export default function CLevelReportPage() {
  const [params, setParams] = useSearchParams()
  const { id } = useParams()
  const snapshotId = id && /^\d+$/.test(id) ? Number(id) : undefined
  const period: CLevelPeriod = params.get('period') === 'month' ? 'month' : 'week'
  const requestedDate = params.get('date')
  const today = cLevelToday()
  const date = requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate : today
  const { report: query, refresh, comment, snapshot } = useCLevelReport(period, date, snapshotId)
  const [selection, setSelection] = useState<CLevelExportSelection>(INITIAL_SELECTION)
  const [detail, setDetail] = useState<{ key: string; violation?: CLevelViolation } | null>(null)
  const [detailError, setDetailError] = useState('')
  const exporter = useCLevelExport()
  const setCurrentReport = useReportStore((state) => state.setCurrentReport)
  const report = query.data
  const isSaved = Boolean(report?.snapshot) || snapshotId !== undefined
  const busy = query.isFetching || refresh.isPending
  useEffect(() => { setCurrentReport(null) }, [setCurrentReport])
  const { reset: resetRefresh } = refresh
  const { reset: resetSnapshot } = snapshot
  useEffect(() => { setDetail(null); setDetailError(''); setSelection(INITIAL_SELECTION); resetRefresh(); resetSnapshot() }, [period, date, snapshotId, resetRefresh, resetSnapshot])
  const updatePeriod = (next: CLevelPeriod, nextDate = date) => setParams({ period: next, date: nextDate })
  const exportReport = (format: 'pdf' | 'xlsx', customersOnly = false) => {
    if (!report) return
    const document = buildCLevelExport(report, { ...selection }, customersOnly)
    void exporter.download(document, format, `C-Level_${customersOnly ? '고객사_' : ''}${report.start_date}_${report.end_date}`)
  }
  const selectedIssue = detail && report?.issues.find((issue) => issue.key === detail.key)
  const selectIssue = (key: string, violation?: CLevelViolation) => {
    if (!report?.issues.some((issue) => issue.key === key)) { setDetailError(`${key} 상세 데이터는 확인 불가입니다. 보고서를 새로고침해 주세요.`); return }
    comment.reset()
    setDetailError('')
    setDetail({ key, violation })
  }
  const displayPeriod = report?.period ?? period
  const currentMonth = displayPeriod === 'month' && report?.end_date.slice(0, 7) === today.slice(0, 7)
  return <div className="cl-page">
    <div className="cl-page-header"><div><p className="cl-breadcrumb">TAC 보고서 / C-Level 보고{isSaved ? ' / 저장된 보고서' : ''}</p><h1>{report?.snapshot?.title || '집중(특별) 관리 보고'}</h1><p className="cl-period-caption">{report ? `${report.start_date} ~ ${report.end_date} (${displayPeriod === 'week' ? '최근 7일' : currentMonth ? '월 누적' : '월간'}) · ${displayPeriod === 'week' ? '전주' : '전월'}(${report.previous_start_date} ~ ${report.previous_end_date}) 대비 · 단순문의 / 인시던트 / 개선` : 'Jira 데이터를 기반으로 처리 현황과 집중 관리 대상을 확인합니다.'}</p></div>
      <div className="cl-actions">
        {!isSaved && <><div className="cl-tabs" aria-label="보고 주기">{(['week', 'month'] as const).map((value) => <button type="button" key={value} aria-pressed={period === value} disabled={refresh.isPending || snapshot.isPending} onClick={() => updatePeriod(value)}>{value === 'week' ? '주간' : '월간'}</button>)}</div><label className="cl-date-picker"><CalendarDays size={15} /><span className="sr-only">{period === 'week' ? '주간 종료일' : '보고 월'}</span><input type={period === 'week' ? 'date' : 'month'} value={period === 'week' ? date : date.slice(0, 7)} max={period === 'week' ? today : today.slice(0, 7)} disabled={refresh.isPending || snapshot.isPending} onChange={(event) => { if (event.target.value) updatePeriod(period, period === 'month' ? `${event.target.value}-01` : event.target.value) }} /></label><button type="button" className="cl-button cl-icon-button" aria-label="Jira 데이터 새로고침" title="Jira 데이터 새로고침" onClick={() => refresh.mutate()} disabled={busy || snapshot.isPending}><RefreshCw size={16} className={refresh.isPending ? 'animate-spin' : ''} /></button><button type="button" className="cl-button" disabled={!report || busy || snapshot.isPending || comment.isPending} onClick={() => snapshot.mutate()}><Save size={15} />{snapshot.isPending ? '저장 중…' : '히스토리에 저장'}</button></>}
        {isSaved && <Link to={`/c-level-report?period=${displayPeriod}&date=${report?.end_date ?? today}`} className="cl-button">새 보고서 조회</Link>}
        <button type="button" className="cl-button cl-button-primary" onClick={() => exportReport('pdf')} disabled={!report || busy || exporter.pending}><Download size={16} />{exporter.pending ? '파일 생성 중…' : 'PDF 내보내기'}</button><button type="button" className="cl-button cl-icon-button" aria-label="전체 보고서 Excel 내보내기" title="전체 보고서 Excel 내보내기" onClick={() => exportReport('xlsx')} disabled={!report || busy || exporter.pending}><Download size={16} /><span className="cl-xlsx-label">XLSX</span></button>
      </div>
    </div>

    {report?.snapshot && <div className="cl-saved-banner"><History size={17} /><div><strong>저장 시점의 수치와 코멘트를 보고 있습니다.</strong><span>{report.snapshot.saved_by} · {cLevelDate(report.snapshot.saved_at)} 저장 · 수정 불가</span></div><Link to="/history">보고서 히스토리</Link></div>}
    {snapshot.isSuccess && snapshot.data && !isSaved && <div className="cl-saved-banner" role="status"><History size={17} /><span>보고서가 히스토리에 저장되었습니다.</span><Link to={`/c-level-report/history/${snapshot.data.id}`}>저장된 보고서 보기</Link></div>}
    {(query.isError || refresh.isError || snapshot.isError || exporter.error || detailError) && <div className="cl-error" role="alert">{exporter.error || detailError || cLevelError(query.error ?? refresh.error ?? snapshot.error)}{query.isError && <button type="button" className="cl-button" onClick={() => void query.refetch()}>다시 조회</button>}</div>}
    {busy && <div className="cl-loading" role="status"><RefreshCw size={22} className="animate-spin" /><div><strong>{refresh.isPending ? 'Jira 최신 데이터를 다시 확인하고 있습니다.' : 'C-Level 보고서를 준비하고 있습니다.'}</strong><p>처리 이력과 SLA 측정 주기를 확인합니다. 최초 조회는 몇 분 걸릴 수 있습니다.</p></div></div>}
    {report && <>
      {report.warnings.length > 0 && <details className="cl-coverage"><summary>집계에 영향을 주는 확인 사항 {report.warnings.length}건</summary><p>확인되지 않은 값은 0으로 계산하지 않고 ‘확인 불가’로 표시합니다.</p><ul>{report.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
      <CLevelOverview report={report} selection={selection} setSelection={setSelection} onSelectIssue={selectIssue} onExportCustomers={() => exportReport('xlsx', true)} exporting={exporter.pending || busy} />
    </>}
    {selectedIssue && detail && report && <CLevelIssueDetail key={`${selectedIssue.key}:${detail.violation?.id ?? ''}`} issue={selectedIssue} violation={detail.violation} comment={report.comments?.[selectedIssue.key]} readonly={isSaved || !report.report_token} saving={comment.isPending} saveError={comment.isError ? cLevelError(comment.error) : ''} onClose={() => setDetail(null)} onSave={async (input) => { try { await comment.mutateAsync({ key: selectedIssue.key, input }); return true } catch { return false } }} />}
  </div>
}
