// frontend/src/presentation/components/charts/RecentIssuesWidget.tsx
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Pin, Search } from 'lucide-react'
import { filterRecentIssuesByElapsedDays } from '@/domain/Issue'
import type { ElapsedDaysComparison, IssueStatusTransitionDays, RecentIssue } from '@/domain/Issue'
import type { IssueColumn, IssueColumnFilters } from '@/domain/IssueColumnSearch'
import { useIssueColumnSearch } from '@/presentation/hooks/useIssueColumnSearch'
import SectionTitle from '@/presentation/components/common/SectionTitle'
import ResolutionTimeChart from '@/presentation/components/charts/ResolutionTimeChart'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import type { IssueContentSource } from '@/presentation/hooks/useIssueContent'

interface Props {
  title?: string
  tablePreferenceKey?: string
  commentsReportId?: number
  detailsSource?: IssueContentSource
  paginationResetKey?: string
  columnFilters?: IssueColumnFilters
  onColumnFilterChange?: (column: IssueColumn, value: string) => void
  onColumnFiltersReset?: () => void
  details: RecentIssue[]
  elapsedDaysThreshold: number | null
  elapsedDaysComparison: ElapsedDaysComparison
  elapsedDaysStatus?: string | null
  elapsedDaysStatuses?: string[]
  statusTransitionDays?: IssueStatusTransitionDays
  statusTransitionHistoryReady?: boolean
  onElapsedDaysFilterChange?: (value: number | null, comparison: ElapsedDaysComparison, status?: string | null) => void
}

export default function RecentIssuesWidget({ title = '최근 이슈 현황', tablePreferenceKey, commentsReportId, detailsSource, paginationResetKey, columnFilters: providedColumnFilters, onColumnFilterChange: providedColumnFilterChange, onColumnFiltersReset, details, elapsedDaysThreshold, elapsedDaysComparison, elapsedDaysStatus = null, elapsedDaysStatuses, statusTransitionDays, statusTransitionHistoryReady = true, onElapsedDaysFilterChange }: Props) {
  const exportMode = useDashboardExportMode()
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState(elapsedDaysThreshold === null ? '' : String(elapsedDaysThreshold))
  const [draftComparison, setDraftComparison] = useState(elapsedDaysComparison)
  const [draftStatus, setDraftStatus] = useState(elapsedDaysStatus)
  const [badInput, setBadInput] = useState(false)
  const [error, setError] = useState('')
  const comparisonLabel = elapsedDaysComparison === 'gte' ? '이상' : '이하'
  const statusHistoryPending = draftStatus !== null && !statusTransitionHistoryReady
  const statusOptions = draftStatus !== null && !elapsedDaysStatuses?.includes(draftStatus)
    ? [...(elapsedDaysStatuses ?? []), draftStatus]
    : elapsedDaysStatuses ?? []
  const elapsedIssues = useMemo(
    () => filterRecentIssuesByElapsedDays(details, elapsedDaysThreshold, elapsedDaysComparison, elapsedDaysStatus, statusTransitionDays),
    [details, elapsedDaysThreshold, elapsedDaysComparison, elapsedDaysStatus, statusTransitionDays],
  )
  const { columnFilters, onColumnFilterChange, filteredIssues } = useIssueColumnSearch(
    elapsedIssues, providedColumnFilters, providedColumnFilterChange,
  )
  const hasResettableColumnFilters = Boolean(onColumnFiltersReset && Object.values(columnFilters).some(Boolean))

  useEffect(() => {
    setDraft(elapsedDaysThreshold === null ? '' : String(elapsedDaysThreshold))
    setDraftComparison(elapsedDaysComparison)
    setDraftStatus(elapsedDaysStatus)
    setBadInput(false)
    setError('')
  }, [elapsedDaysThreshold, elapsedDaysComparison, elapsedDaysStatus])

  const search = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (statusHistoryPending) return
    const value = draft.trim() === '' ? null : Number(draft)
    if (inputRef.current?.validity.badInput || (value !== null && (!Number.isSafeInteger(value) || value < 0))) {
      setError('0 이상의 정수를 입력해 주세요.')
      return
    }
    setError('')
    onElapsedDaysFilterChange?.(value, draftComparison, draftStatus)
  }

  const reset = () => {
    if (inputRef.current) inputRef.current.value = ''
    setDraft('')
    setDraftComparison('gte')
    setDraftStatus(null)
    setBadInput(false)
    setError('')
    onElapsedDaysFilterChange?.(null, 'gte', null)
    onColumnFiltersReset?.()
  }

  return (
    <div data-pdf-section={title} className="space-y-2">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className={`min-w-0 max-w-full [&>div]:flex-wrap ${!exportMode && onElapsedDaysFilterChange ? 'pt-2' : ''}`}>
          <SectionTitle icon={Pin} title={title} subtitle={elapsedDaysThreshold === null
            ? `${title === '최근 이슈 현황' ? '최신' : '전체'} ${filteredIssues.length}건`
            : `${elapsedDaysStatus === null ? '' : `${elapsedDaysStatus} 전이 후 · `}${elapsedDaysThreshold}일 ${comparisonLabel} · ${filteredIssues.length}건`} />
        </div>
        {!exportMode && onElapsedDaysFilterChange && (
          <form onSubmit={search} noValidate className="ml-auto flex w-full min-w-0 max-w-full flex-col gap-2 sm:w-auto sm:items-end" aria-label="최근 이슈 경과일 검색">
            <div className="flex min-w-0 max-w-full flex-wrap items-center justify-end gap-2">
              {elapsedDaysStatuses === undefined ? (
                <label htmlFor={inputId} className="text-control-label font-medium text-apple-mid">경과일</label>
              ) : (
                <select
                  value={draftStatus ?? ''}
                  onChange={(event) => { setDraftStatus(event.target.value || null); setError('') }}
                  aria-label="경과일 기준"
                  className="h-10 w-full min-w-0 max-w-full shrink-0 cursor-pointer rounded-lg border border-apple-divider bg-apple-surface px-3 text-control text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 sm:w-48"
                >
                  <option value="">경과일</option>
                  {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              )}
              <div className="flex max-w-full shrink-0 items-center gap-2">
                <input
                  ref={inputRef}
                  id={inputId}
                  type="number"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  value={draft}
                  onChange={(event) => {
                    setDraft(event.target.value)
                    setError('')
                  }}
                  onInput={(event) => { setBadInput(event.currentTarget.validity.badInput); setError('') }}
                  placeholder="전체"
                  aria-label="최근 이슈 경과일"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? `${inputId}-error` : undefined}
                  className="h-10 w-24 rounded-lg border border-apple-divider bg-apple-surface px-3 text-control tabular-nums text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
                <span className="text-label text-apple-mid">일</span>
                <select
                  value={draftComparison}
                  onChange={(event) => setDraftComparison(event.target.value === 'lte' ? 'lte' : 'gte')}
                  aria-label="최근 이슈 경과일 조건"
                  className="h-10 cursor-pointer rounded-lg border border-apple-divider bg-apple-surface px-3 text-control text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                >
                  <option value="gte">이상</option>
                  <option value="lte">이하</option>
                </select>
              </div>
              <div className="flex max-w-full shrink-0 items-center gap-2">
                <button type="submit" disabled={statusHistoryPending} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-control font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-wait disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2">
                  <Search size={14} aria-hidden="true" />
                  검색
                </button>
                <button type="button" onClick={reset} disabled={elapsedDaysThreshold === null && draft === '' && elapsedDaysComparison === 'gte' && draftComparison === 'gte' && elapsedDaysStatus === null && draftStatus === null && !badInput && !hasResettableColumnFilters} className="min-h-10 rounded-lg px-3 text-control font-medium text-apple-mid transition-colors hover:bg-apple-gray disabled:cursor-default disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2">
                  초기화
                </button>
              </div>
            </div>
            {error && <p id={`${inputId}-error`} role="alert" className="max-w-full break-keep text-right text-label text-red-600">{error}</p>}
            {statusHistoryPending && <p role="status" className="max-w-full break-keep text-right text-label text-apple-mid">상태 전이 이력을 수집 중입니다. 완료 후 검색할 수 있습니다.</p>}
            {draftStatus !== null && !statusHistoryPending && <p className="max-w-full break-keep text-right text-label text-apple-mid">현재 상태와 관계없이 최근 전이일 기준 · 한국 시간</p>}
          </form>
        )}
      </div>
      <ResolutionTimeChart
        title={title}
        tablePreferenceKey={tablePreferenceKey}
        commentsReportId={commentsReportId}
        detailsSource={detailsSource}
        details={filteredIssues}
        paginationResetKey={JSON.stringify([paginationResetKey, elapsedDaysThreshold, elapsedDaysComparison, elapsedDaysStatus, columnFilters])}
        columnFilters={columnFilters}
        onColumnFilterChange={onColumnFilterChange}
        emptyMessage={elapsedDaysThreshold === null ? undefined : `${elapsedDaysStatus === null ? '경과일이' : `${elapsedDaysStatus} 전이 후`} ${elapsedDaysThreshold}일 ${comparisonLabel}인 이슈가 없습니다.`}
      />
    </div>
  )
}
