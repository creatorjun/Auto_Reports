// frontend/src/presentation/components/charts/RecentIssuesWidget.tsx
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Pin, Search } from 'lucide-react'
import { filterRecentIssuesByElapsedDays } from '@/domain/Issue'
import type { ElapsedDaysComparison, RecentIssue } from '@/domain/Issue'
import SectionTitle from '@/presentation/components/common/SectionTitle'
import ResolutionTimeChart from '@/presentation/components/charts/ResolutionTimeChart'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'

interface Props {
  title?: string
  paginationResetKey?: string
  details: RecentIssue[]
  elapsedDaysThreshold: number | null
  elapsedDaysComparison: ElapsedDaysComparison
  onElapsedDaysFilterChange?: (value: number | null, comparison: ElapsedDaysComparison) => void
}

export default function RecentIssuesWidget({ title = '최근 이슈 현황', paginationResetKey, details, elapsedDaysThreshold, elapsedDaysComparison, onElapsedDaysFilterChange }: Props) {
  const exportMode = useDashboardExportMode()
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState(elapsedDaysThreshold === null ? '' : String(elapsedDaysThreshold))
  const [draftComparison, setDraftComparison] = useState(elapsedDaysComparison)
  const [badInput, setBadInput] = useState(false)
  const [error, setError] = useState('')
  const comparisonLabel = elapsedDaysComparison === 'gte' ? '이상' : '이하'
  const filteredIssues = useMemo(
    () => filterRecentIssuesByElapsedDays(details, elapsedDaysThreshold, elapsedDaysComparison),
    [details, elapsedDaysThreshold, elapsedDaysComparison],
  )

  useEffect(() => {
    setDraft(elapsedDaysThreshold === null ? '' : String(elapsedDaysThreshold))
    setDraftComparison(elapsedDaysComparison)
    setBadInput(false)
    setError('')
  }, [elapsedDaysThreshold, elapsedDaysComparison])

  const search = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const value = draft.trim() === '' ? null : Number(draft)
    if (inputRef.current?.validity.badInput || (value !== null && (!Number.isSafeInteger(value) || value < 0))) {
      setError('0 이상의 정수를 입력해 주세요.')
      return
    }
    setError('')
    onElapsedDaysFilterChange?.(value, draftComparison)
  }

  const reset = () => {
    if (inputRef.current) inputRef.current.value = ''
    setDraft('')
    setDraftComparison('gte')
    setBadInput(false)
    setError('')
    onElapsedDaysFilterChange?.(null, 'gte')
  }

  return (
    <div data-pdf-section="최근 이슈 현황" className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle icon={Pin} title={title} subtitle={elapsedDaysThreshold === null
          ? `${title === '최근 이슈 현황' ? '최신' : '전체'} ${filteredIssues.length}건`
          : `${elapsedDaysThreshold}일 ${comparisonLabel} · ${filteredIssues.length}건`} />
        {!exportMode && onElapsedDaysFilterChange && (
          <form onSubmit={search} noValidate className="flex max-w-full flex-wrap items-center gap-2" aria-label="최근 이슈 경과일 검색">
            <label htmlFor={inputId} className="text-ui-sm font-medium text-apple-mid">경과일</label>
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
              className="h-10 w-24 rounded-lg border border-apple-divider bg-apple-surface px-3 text-ui-sm tabular-nums text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <span className="text-ui-sm text-apple-mid">일</span>
            <select
              value={draftComparison}
              onChange={(event) => setDraftComparison(event.target.value === 'lte' ? 'lte' : 'gte')}
              aria-label="최근 이슈 경과일 조건"
              className="h-10 cursor-pointer rounded-lg border border-apple-divider bg-apple-surface px-3 text-ui-sm text-apple-dark focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            >
              <option value="gte">이상</option>
              <option value="lte">이하</option>
            </select>
            <button type="submit" className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-ui-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2">
              <Search size={14} aria-hidden="true" />
              검색
            </button>
            <button type="button" onClick={reset} disabled={elapsedDaysThreshold === null && draft === '' && elapsedDaysComparison === 'gte' && draftComparison === 'gte' && !badInput} className="min-h-10 rounded-lg px-3 text-ui-sm font-medium text-apple-mid transition-colors hover:bg-apple-gray disabled:cursor-default disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2">
              초기화
            </button>
            {error && <p id={`${inputId}-error`} role="alert" className="w-full text-ui-sm text-red-600">{error}</p>}
          </form>
        )}
      </div>
      <ResolutionTimeChart
        details={filteredIssues}
        paginationResetKey={paginationResetKey}
        emptyMessage={elapsedDaysThreshold === null ? undefined : `경과일이 ${elapsedDaysThreshold}일 ${comparisonLabel}인 이슈가 없습니다.`}
      />
    </div>
  )
}
