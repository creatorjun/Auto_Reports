// frontend/src/presentation/pages/IssueManagementPage.tsx
import { useCallback, useMemo, useRef, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import type { Semester } from '@/domain/Dashboard'
import type { ElapsedDaysComparison, RecentIssue } from '@/domain/Issue'
import type { DashboardExportFormat, DashboardPdfDocument } from '@/domain/DashboardExport'
import type { IssueColumnFilters } from '@/domain/IssueColumnSearch'
import { filterManagedIssues } from '@/domain/IssueManagement'
import { filterIssuesByColumns } from '@/domain/IssueColumnSearch'
import { sortDashboardStatuses } from '@/domain/DashboardStatusPolicy'
import { useIssueManagement } from '@/presentation/hooks/useIssueManagement'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import RecentIssuesWidget from '@/presentation/components/charts/RecentIssuesWidget'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import DashboardPdfExportStage from '@/presentation/components/export/DashboardPdfExportStage'
import { ISSUE_COLUMNS } from '@/presentation/config/issueColumns'
import { getIssueTypeLabel } from '@/presentation/utils/issueTypeLabel'
import '@/presentation/styles/dashboardExport.css'

interface ExportSnapshot {
  details: RecentIssue[]
  columnFilters: IssueColumnFilters
  elapsed: number | null
  comparison: ElapsedDaysComparison
  format: DashboardExportFormat
  metadata: Omit<DashboardPdfDocument, 'sections'>
  fileName: string
}

export default function IssueManagementPage() {
  const query = useIssueManagement()
  const [types, setTypes] = useState<Set<string> | null>(null)
  const [statuses, setStatuses] = useState<Set<string> | null>(null)
  const [semester, setSemester] = useState<Semester | null>(null)
  const [titleSearch, setTitleSearch] = useState('')
  const [elapsed, setElapsed] = useState<number | null>(null)
  const [comparison, setComparison] = useState<ElapsedDaysComparison>('gte')
  const [columnFilters, setColumnFilters] = useState<IssueColumnFilters>({})
  const [exportFormat, setExportFormat] = useState<DashboardExportFormat>('pdf')
  const [exportSnapshot, setExportSnapshot] = useState<ExportSnapshot | null>(null)
  const [exportError, setExportError] = useState('')
  const exportPending = useRef(false)
  const issues = query.data?.issues
  const options = useMemo(() => ({
    types: [...new Set(issues?.map((issue) => issue.type) ?? [])].sort(),
    statuses: sortDashboardStatuses(issues?.map((issue) => issue.status) ?? []),
  }), [issues])
  const details = useMemo(() => filterIssuesByColumns(filterManagedIssues(issues ?? [], types, statuses, semester, null), { summary: titleSearch }), [issues, types, statuses, semester, titleSearch])
  const toggle = (current: Set<string> | null, all: string[], value: string) => {
    const next = new Set(current ?? all)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next.size === all.length && all.every((item) => next.has(item)) ? null : next
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
    if (exportPending.current || !query.data?.initialized) return
    const now = new Date()
    const filters = [
      '전체 연도',
      semester === 'h1' ? '상반기' : semester === 'h2' ? '하반기' : '전체 기간',
      types === null ? '전체 업무 유형' : types.size ? [...types].map(getIssueTypeLabel).join(', ') : '선택된 업무 유형 없음',
      statuses === null ? '전체 현재 상태' : statuses.size ? [...statuses].join(', ') : '선택된 현재 상태 없음',
    ]
    if (titleSearch.trim()) filters.push(`제목 검색: ${titleSearch.trim()}`)
    if (elapsed !== null) filters.push(`경과일 ${elapsed}일 ${comparison === 'gte' ? '이상' : '이하'}`)
    for (const { key, label } of ISSUE_COLUMNS) {
      const value = columnFilters[key]?.trim()
      if (value) filters.push(`${label} 컬럼 검색: ${value}`)
    }
    if (query.data.synced_at) filters.push(`마지막 동기화 ${new Date(query.data.synced_at).toLocaleString('ko-KR')}`)
    const snapshot: ExportSnapshot = {
      details: details.map((issue) => ({ ...issue })),
      columnFilters: { ...columnFilters },
      elapsed,
      comparison,
      format: exportFormat,
      metadata: {
        title: '이슈 관리',
        period: 'TACEA 전체 요청 · 완료 항목 포함',
        generatedAt: now.toLocaleString('ko-KR', { hour12: false }),
        filters,
      },
      fileName: `TACEA_이슈_목록_${now.toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' })}.${exportFormat}`,
    }
    exportPending.current = true
    setExportError('')
    setExportSnapshot(snapshot)
  }

  return (
    <div className="dashboard-view space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-apple-dark">이슈 관리</h1>
          <p className="mt-1 text-ui-sm text-apple-mid">TACEA 전체 요청 · 완료 항목 포함 · 30초마다 변경분 동기화</p>
          <p className="mt-1 text-xs text-apple-light" aria-live="polite">{query.data?.synced_at ? `마지막 동기화 ${new Date(query.data.synced_at).toLocaleString('ko-KR')}` : '전체 이슈를 수집하고 있습니다.'}{query.data?.refreshing ? ' · 동기화 중' : ''}</p>
        </div>
        <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-ui-sm font-semibold text-white disabled:opacity-50">
          <RefreshCw size={16} className={query.isFetching || query.data?.refreshing ? 'animate-spin' : ''} />새로고침
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-3">
        <span className="text-[12px] text-apple-mid">현재 필터 · 컬럼 검색 · 표 전체 포함</span>
        <select aria-label="다운로드 형식" value={exportFormat} onChange={(event) => setExportFormat(event.target.value as DashboardExportFormat)} disabled={exportSnapshot !== null}
          className="rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-[13px] font-medium text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-60">
          <option value="pdf">PDF</option>
          <option value="xlsx">Excel (.xlsx)</option>
        </select>
        <button type="button" onClick={startExport} disabled={exportSnapshot !== null || !query.data?.initialized} aria-busy={exportSnapshot !== null}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-wait disabled:opacity-60">
          {exportSnapshot ? <RefreshCw size={16} className="animate-spin" /> : <Download size={16} />}
          <span aria-live="polite">{exportSnapshot ? `${exportSnapshot.format === 'xlsx' ? 'Excel' : 'PDF'} 생성 중...` : `${exportFormat === 'xlsx' ? 'Excel' : 'PDF'} 내보내기`}</span>
        </button>
        {exportError && <p role="alert" className="w-full text-right text-[13px] text-red-600">{exportError}</p>}
      </div>
      {(query.isError || query.data?.error) && <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{query.data?.error ?? '이슈 조회에 실패했습니다. 기존 목록을 유지하며 자동 재시도합니다.'}</p>}
      <IssueTypeFilter issueTypes={options.types} statuses={options.statuses} selectedTypes={types} selectedStatuses={statuses} selectedSemester={semester} supported statusSupported semesterSupported
        titleSearch={titleSearch} onTitleSearchChange={setTitleSearch}
        onToggle={(value) => setTypes((current) => toggle(current, options.types, value))}
        onStatusToggle={(value) => setStatuses((current) => toggle(current, options.statuses, value))}
        onSemesterChange={setSemester}
        onToggleAll={(selected) => { setTypes(selected ? null : new Set()); setStatuses(selected ? null : new Set()) }} />
      {!query.data?.initialized && !query.data?.error && !query.isError ? <LoadingSpinner text="TACEA 전체 이슈 수집 중..." /> : (
        <RecentIssuesWidget title="전체 이슈 현황" paginationResetKey={JSON.stringify([types === null ? null : [...types].sort(), statuses === null ? null : [...statuses].sort(), semester, elapsed, comparison, titleSearch])}
          details={details} elapsedDaysThreshold={elapsed} elapsedDaysComparison={comparison} onElapsedDaysFilterChange={(value, condition) => { setElapsed(value); setComparison(condition) }}
          columnFilters={columnFilters} onColumnFilterChange={(column, value) => setColumnFilters((current) => ({ ...current, [column]: value }))} />
      )}
      {exportSnapshot && (
        <DashboardPdfExportStage format={exportSnapshot.format} metadata={exportSnapshot.metadata} fileName={exportSnapshot.fileName} onComplete={finishExport} onError={failExport}>
          <RecentIssuesWidget title="전체 이슈 현황" details={exportSnapshot.details} elapsedDaysThreshold={exportSnapshot.elapsed} elapsedDaysComparison={exportSnapshot.comparison} columnFilters={exportSnapshot.columnFilters} />
        </DashboardPdfExportStage>
      )}
    </div>
  )
}
