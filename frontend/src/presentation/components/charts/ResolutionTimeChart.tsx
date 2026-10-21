// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { Fragment, useState, useRef, useCallback, useMemo, useEffect, useId } from 'react'
import { ChevronDown } from 'lucide-react'
import { useJira } from '@/presentation/context/JiraContext'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { TABLE_PAGE_SIZE, TABLE_MIN_COL_FRAC } from '@/presentation/config/constants'
import type { RecentIssue } from '@/domain/Issue'
import { issueTypeLabel } from '@/domain/Issue'
import type { IssueColumn, IssueColumnFilters } from '@/domain/IssueColumnSearch'
import ColumnSearchInput from '@/presentation/components/common/ColumnSearchInput'
import { ISSUE_COLUMNS } from '@/presentation/config/issueColumns'
import { useTablePreferences } from '@/presentation/hooks/useTablePreferences'
import IssueDetailsPanel from '@/presentation/components/common/IssueDetailsPanel'

const COLS = ISSUE_COLUMNS.map((column) => column.key)
type ColKey = IssueColumn
type SortDir = 'asc' | 'desc'

const DEFAULT_FRACS: Record<ColKey, number> = {
  key:      0.10,
  summary:  0.22,
  type:     0.10,
  status:   0.11,
  reporter: 0.10,
  tac:      0.10,
  tac_assignee: 0.13,
  elapsed:  0.14,
}

interface Props {
  title?: string
  tablePreferenceKey?: string
  commentsReportId?: number
  details: RecentIssue[]
  emptyMessage?: string
  paginationResetKey?: string
  columnFilters?: IssueColumnFilters
  onColumnFilterChange?: (column: IssueColumn, value: string) => void
}

function SortIcon({ dir }: { dir: SortDir | null }) {
  if (!dir) return <span className="ml-1 opacity-30 text-caption">⇅</span>
  return <span className="ml-1 text-brand-500 text-caption">{dir === 'asc' ? '↑' : '↓'}</span>
}

function ResizeHandle({ onDrag, tableWidth }: { onDrag: (frac: number) => void; tableWidth: React.RefObject<number> }) {
  const dragging  = useRef(false)
  const hasMoved  = useRef(false)
  const lastX     = useRef(0)
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault(); e.stopPropagation()
    dragging.current = true; hasMoved.current = false; lastX.current = e.clientX
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [])
  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return
    const dx = e.clientX - lastX.current; lastX.current = e.clientX
    if (dx !== 0) hasMoved.current = true
    onDrag(dx / (tableWidth.current || 1))
  }, [onDrag, tableWidth])
  const onPointerUp = useCallback(() => { dragging.current = false }, [])
  const onClickCapture = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
  }, [])
  return (
    <span
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onClick={onClickCapture}
      className="absolute right-0 top-0 h-full w-[6px] cursor-col-resize select-none flex items-center justify-center group z-10"
      title="드래그하여 너비 조절"
    >
      <span className="h-6 w-[2px] rounded bg-apple-mid/60 transition-colors group-hover:bg-brand-500" />
    </span>
  )
}

function sortIssues(items: RecentIssue[], key: ColKey, dir: SortDir): RecentIssue[] {
  return [...items].sort((a, b) => {
    let av: string | number = ''
    let bv: string | number = ''
    switch (key) {
      case 'key':      av = a.key;          bv = b.key;          break
      case 'summary':  av = a.summary;      bv = b.summary;      break
      case 'type':     av = issueTypeLabel(a.type); bv = issueTypeLabel(b.type); break
      case 'status':   av = a.stage_index;  bv = b.stage_index;  break
      case 'reporter': av = a.reporter;     bv = b.reporter;     break
      case 'tac':      av = a.tac_team;     bv = b.tac_team;     break
      case 'tac_assignee': av = a.tac_assignee ?? ''; bv = b.tac_assignee ?? ''; break
      case 'elapsed':  av = a.elapsed_days; bv = b.elapsed_days; break
    }
    if (av < bv) return dir === 'asc' ? -1 : 1
    if (av > bv) return dir === 'asc' ?  1 : -1
    return 0
  })
}

function useDesktopDetailsLayout(enabled: boolean) {
  const [isDesktop, setIsDesktop] = useState(() => typeof window === 'undefined' || !window.matchMedia
    ? true
    : window.matchMedia('(min-width: 768px)').matches)
  useEffect(() => {
    if (!enabled || typeof window === 'undefined' || !window.matchMedia) return
    const media = window.matchMedia('(min-width: 768px)')
    const update = () => setIsDesktop(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [enabled])
  return isDesktop
}

function DetailsToggle({ issueKey, expanded, panelId, onToggle }: {
  issueKey: string
  expanded: boolean
  panelId: string
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      aria-label={`${issueKey} 상세 ${expanded ? '접기' : '펼치기'}`}
      aria-expanded={expanded}
      aria-controls={expanded ? panelId : undefined}
      onClick={(event) => { event.stopPropagation(); onToggle() }}
      className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      <ChevronDown size={18} aria-hidden="true" className={expanded ? 'rotate-180' : ''} />
    </button>
  )
}

function MobileIssueCard({ issue, jiraBase, commentsReportId, expanded, panelId, onToggle, showPanel }: {
  issue: RecentIssue
  jiraBase: string
  commentsReportId?: number
  expanded: boolean
  panelId: string
  onToggle: () => void
  showPanel: boolean
}) {
  const jiraUrl = `${jiraBase}/browse/${issue.key}`
  const createdDate = issue.created ? issue.created.slice(0, 10) : '-'
  return (
    <>
      <div
        onClick={() => window.open(jiraUrl, '_blank', 'noreferrer')}
        className="flex flex-col items-center gap-2 px-4 py-3 text-center hover:bg-gray-50 active:bg-gray-100 transition-colors cursor-pointer"
      >
        <div className="flex max-w-full flex-wrap items-center justify-center gap-2">
          <span className="font-mono text-caption text-blue-500 flex-shrink-0">{issue.key}</span>
          <StatusBadge status={issue.status} size="xs" />
        </div>
        <p className="w-full break-words text-body text-apple-dark leading-snug">{issue.summary}</p>
        <span className="text-caption text-apple-mid">티켓 타입 · <IssueTypeBadge type={issueTypeLabel(issue.type)} className="max-w-full whitespace-normal break-words" /></span>
        <div className="flex flex-wrap items-center justify-center gap-2 text-caption text-apple-light">
          <span>{issue.reporter}</span>
          <span className="text-apple-divider">·</span>
          <span>{issue.tac_team}</span>
        </div>
        <div className="flex max-w-full items-start justify-center gap-1 text-caption text-apple-light">
          <span className="shrink-0">TAC 담당자</span>
          <span className="min-w-0 break-words font-medium text-apple-dark">{issue.tac_assignee ?? '-'}</span>
        </div>
        <div className="flex items-center justify-center gap-1 text-caption text-apple-light">
          <span className="tabular-nums">{createdDate}</span>
          <span className="text-apple-divider">·</span>
          <span className="tabular-nums font-medium text-amber-600">{issue.elapsed_days}일 경과</span>
        </div>
        {commentsReportId !== undefined && <DetailsToggle issueKey={issue.key} expanded={expanded} panelId={panelId} onToggle={onToggle} />}
      </div>
      {showPanel && commentsReportId !== undefined && (
        <div id={panelId} className="px-3 pb-4">
          <IssueDetailsPanel issueKey={issue.key} reportId={commentsReportId} />
        </div>
      )}
    </>
  )
}

export default function ResolutionTimeChart({ title = '최근 이슈 현황', tablePreferenceKey, commentsReportId, details, paginationResetKey, columnFilters, onColumnFilterChange, emptyMessage = '최근 이슈 데이터가 없습니다.' }: Props) {
  const exportMode = useDashboardExportMode()
  const detailsEnabled = commentsReportId !== undefined && !exportMode
  const isDesktopDetailsLayout = useDesktopDetailsLayout(detailsEnabled)
  const detailsId = useId()
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set())
  const { jiraBase } = useJira()
  const [page,    setPage]    = useState(1)
  const { sort, setSort, widths: fracs, setWidths: setFracs } = useTablePreferences(exportMode ? undefined : tablePreferenceKey, DEFAULT_FRACS, TABLE_MIN_COL_FRAC)
  const sortKey = sort?.key ?? null
  const sortDir = sort?.direction ?? 'asc'
  const tableRef      = useRef<HTMLTableElement>(null)
  const tableWidthRef = useRef<number>(0)

  const previousResetKey = useRef(paginationResetKey)
  useEffect(() => {
    if (paginationResetKey === undefined || previousResetKey.current !== paginationResetKey) setPage(1)
    else setPage((current) => Math.min(current, Math.max(1, Math.ceil(details.length / TABLE_PAGE_SIZE))))
    previousResetKey.current = paginationResetKey
  }, [details, paginationResetKey])

  const handleSort = useCallback((col: ColKey) => {
    setSort((previous) => ({ key: col, direction: previous?.key === col && previous.direction === 'asc' ? 'desc' : 'asc' }))
    setPage(1)
  }, [setSort])

  const toggleDetails = (issueKey: string) => {
    setExpandedKeys((current) => {
      const next = new Set(current)
      if (next.has(issueKey)) next.delete(issueKey)
      else next.add(issueKey)
      return next
    })
  }

  const resize = useCallback((leftCol: ColKey, rightCol: ColKey, df: number) => {
    setFracs((prev) => {
      const newLeft  = Math.max(TABLE_MIN_COL_FRAC, prev[leftCol]  + df)
      const newRight = Math.max(TABLE_MIN_COL_FRAC, prev[rightCol] - df)
      if (newLeft + newRight !== prev[leftCol] + prev[rightCol]) return prev
      return { ...prev, [leftCol]: newLeft, [rightCol]: newRight }
    })
  }, [setFracs])

  const getTableWidth = useCallback(() => {
    tableWidthRef.current = tableRef.current?.offsetWidth ?? tableWidthRef.current
    return tableWidthRef
  }, [])

  const sortedDetails = useMemo(
    () => sortKey ? sortIssues(details, sortKey, sortDir) : details,
    [details, sortKey, sortDir],
  )
  const hasColumnSearch = Object.values(columnFilters ?? {}).some((value) => value?.trim())
  const noResultsMessage = hasColumnSearch ? '검색 조건에 맞는 이슈가 없습니다.' : emptyMessage

  if (details.length === 0 && (exportMode || !onColumnFilterChange)) {
    return (
      <div data-pdf-kind="table" data-pdf-title={title} className="card flex items-center justify-center h-48 text-apple-light text-body">
        {noResultsMessage}
      </div>
    )
  }

  const totalPages = Math.ceil(sortedDetails.length / TABLE_PAGE_SIZE)
  const pageNumbers = paginationResetKey === undefined
    ? Array.from({ length: totalPages }, (_, index) => index + 1)
    : [...new Set([1, totalPages, page - 2, page - 1, page, page + 1, page + 2])].filter((value) => value >= 1 && value <= totalPages).sort((a, b) => a - b)
  const pageItems  = sortedDetails.slice((page - 1) * TABLE_PAGE_SIZE, page * TABLE_PAGE_SIZE)
  const visibleItems = exportMode ? sortedDetails : pageItems

  const headers = ISSUE_COLUMNS.map((column, index) => ({ ...column, rightCol: ISSUE_COLUMNS[index + 1]?.key }))
  const searchInput = (key: ColKey, label: string, mobile = false) => (
    <ColumnSearchInput label={label} value={columnFilters?.[key] ?? ''} mobile={mobile}
      onChange={(value) => onColumnFilterChange?.(key, value)} />
  )

  return (
    <div data-pdf-kind="table" data-pdf-title={title} className="card p-0 overflow-hidden">
      <div data-pdf-mobile="" className="md:hidden">
        {!exportMode && onColumnFilterChange && <div className="grid grid-cols-2 gap-3 border-b border-apple-divider p-4">{headers.map(({ key, label }) => <label key={key} className="text-control-label font-semibold text-apple-mid">{label}{searchInput(key, label, true)}</label>)}</div>}
        {pageItems.length === 0 && <p className="p-6 text-center text-label text-apple-light">{noResultsMessage}</p>}
        {pageItems.map((issue) => (
          <MobileIssueCard key={issue.key} issue={issue} jiraBase={jiraBase}
            commentsReportId={detailsEnabled ? commentsReportId : undefined}
            expanded={expandedKeys.has(issue.key)}
            panelId={`${detailsId}-mobile-${issue.key}`}
            onToggle={() => toggleDetails(issue.key)}
            showPanel={detailsEnabled && !isDesktopDetailsLayout && expandedKeys.has(issue.key)} />
        ))}
      </div>

      <div data-pdf-desktop="" className="hidden md:block overflow-x-auto">
        <table data-pdf-table-layout="recent" ref={tableRef} className={`w-full ${detailsEnabled ? 'min-w-[1220px]' : 'min-w-[1160px]'} text-body border-collapse`} style={{ tableLayout: 'fixed' }}>
          <colgroup>
            {COLS.map((col) => <col key={col} style={{ width: `${(fracs[col] * (detailsEnabled ? 95 : 100)).toFixed(2)}%` }} />)}
            {detailsEnabled && <col style={{ width: '5%' }} />}
          </colgroup>
          <thead className="bg-apple-gray/60">
            <tr className="border-b-2 border-apple-divider text-label text-apple-mid">
              {headers.map(({ key, label, rightCol }) => (
                <th key={key} data-pdf-header={label} onClick={() => handleSort(key)}
                  className={['relative cursor-pointer select-none whitespace-normal break-words border-r border-apple-divider/90 px-3 pb-2.5 pt-3 text-center font-semibold transition-colors last:border-r-0 hover:bg-apple-gray hover:text-apple-primary', sortKey === key ? 'text-apple-primary' : ''].join(' ')}>
                  <span className="inline-flex max-w-full flex-wrap items-center justify-center">
                    {label}<SortIcon dir={sortKey === key ? sortDir : null} />
                  </span>
                  {!exportMode && onColumnFilterChange && searchInput(key, label)}
                  {rightCol && <ResizeHandle tableWidth={getTableWidth()} onDrag={(df) => resize(key, rightCol, df)} />}
                </th>
              ))}
              {detailsEnabled && <th scope="col"><span className="sr-only">상세</span></th>}
            </tr>
          </thead>
          <tbody>
            {visibleItems.length === 0 && <tr><td colSpan={headers.length + (detailsEnabled ? 1 : 0)} className="px-4 py-10 text-center text-apple-light">{noResultsMessage}</td></tr>}
            {visibleItems.map((issue) => {
              const jiraUrl = `${jiraBase}/browse/${issue.key}`
              const createdDate = issue.created ? issue.created.slice(0, 10) : '-'
              const expanded = expandedKeys.has(issue.key)
              const panelId = `${detailsId}-desktop-${issue.key}`
              return (
                <Fragment key={issue.key}>
                  <tr onClick={() => window.open(jiraUrl, '_blank', 'noreferrer')}
                    className="cursor-pointer transition-colors hover:bg-gray-50">
                    <td className="px-3 py-2 text-center" data-pdf-link={jiraUrl}><span className="block break-all font-mono text-label text-blue-500">{issue.key}</span></td>
                    <td className="px-3 py-2 text-center"><span className="block break-words text-apple-primary">{issue.summary}</span></td>
                    <td className="overflow-hidden px-3 py-2 text-center"><IssueTypeBadge type={issueTypeLabel(issue.type)} className="max-w-full whitespace-normal break-words" /></td>
                    <td className="overflow-hidden px-3 py-2 text-center">
                      <StatusBadge status={issue.status} size="md" />
                    </td>
                    <td className="px-3 py-2 text-center"><span className="block break-words text-label text-apple-light">{issue.reporter}</span></td>
                    <td className="px-3 py-2 text-center"><span className="block break-words text-label text-apple-light">{issue.tac_team}</span></td>
                    <td className="px-3 py-2 text-center"><span className="block break-words text-label text-apple-light">{issue.tac_assignee ?? '-'}</span></td>
                    <td className="px-3 py-2 text-center text-apple-light" data-pdf-value={`${createdDate}\n(${issue.elapsed_days}일 경과)`}>
                      <div className="flex flex-wrap items-center justify-center gap-x-1">
                        <span className="break-all tabular-nums">{createdDate}</span>
                        <span className="text-caption text-apple-divider">·</span>
                        <span className="break-all tabular-nums">{issue.elapsed_days}일</span>
                      </div>
                    </td>
                    {detailsEnabled && <td className="px-2 py-2 text-center">
                      <DetailsToggle issueKey={issue.key} expanded={expanded} panelId={panelId} onToggle={() => toggleDetails(issue.key)} />
                    </td>}
                  </tr>
                  {detailsEnabled && commentsReportId !== undefined && isDesktopDetailsLayout && expanded && (
                    <tr>
                      <td colSpan={headers.length + 1} className="px-4 pb-4 pt-1">
                        <div id={panelId}><IssueDetailsPanel issueKey={issue.key} reportId={commentsReportId} /></div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {!exportMode && totalPages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 md:px-5 py-3 mt-0 border-t border-apple-divider">
          <span className="text-label text-apple-light">{(page - 1) * TABLE_PAGE_SIZE + 1}–{Math.min(page * TABLE_PAGE_SIZE, sortedDetails.length)} / {sortedDetails.length}건</span>
          <div className="flex flex-wrap items-center gap-1">
            {paginationResetKey !== undefined && <button type="button" aria-label="이전 페이지" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="rounded bg-gray-100 px-3 py-1 text-control text-apple-mid disabled:opacity-40">이전</button>}
            {pageNumbers.map((value, index) => (
              <span key={value} className="inline-flex items-center gap-1">
                {index > 0 && value - pageNumbers[index - 1] > 1 && <span className="px-1 text-apple-light">…</span>}
                <button type="button" aria-current={page === value ? 'page' : undefined} onClick={(event) => { event.stopPropagation(); setPage(value) }}
                  className={`px-3 py-1 rounded text-control font-medium transition-colors ${page === value ? 'bg-brand-500 text-white' : 'bg-gray-100 text-apple-mid hover:bg-gray-200'}`}>{value}</button>
              </span>
            ))}
            {paginationResetKey !== undefined && <button type="button" aria-label="다음 페이지" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className="rounded bg-gray-100 px-3 py-1 text-control text-apple-mid disabled:opacity-40">다음</button>}
          </div>
        </div>
      )}
    </div>
  )
}
