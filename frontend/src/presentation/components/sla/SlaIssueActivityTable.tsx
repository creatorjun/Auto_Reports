// frontend/src/presentation/components/sla/SlaIssueActivityTable.tsx
import { useEffect, useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ExternalLink } from 'lucide-react'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { IssueTypeIcon } from '@/presentation/components/common/IssueTypeIcon'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import { useJira } from '@/presentation/context/JiraContext'
import IssueCommentsPanel from '@/presentation/components/common/IssueCommentsPanel'
import type { SlaDashboardIssue } from '@/domain/SlaDashboard'

const SLA_DESKTOP_MEDIA_QUERY = '(min-width: 1280px)'
const SORT_COLUMNS = [
  { key: 'key', label: '티켓 번호' },
  { key: 'summary', label: '티켓 제목' },
  { key: 'created', label: '생성일' },
  { key: 'status', label: '진행상태' },
] as const
type SortKey = typeof SORT_COLUMNS[number]['key']
type SortState = { key: SortKey; direction: 'asc' | 'desc' }
const SORT_COLLATOR = new Intl.Collator('ko', { numeric: true, sensitivity: 'base' })

function useIsDesktopSlaLayout(): boolean {
  const [isDesktop, setIsDesktop] = useState(
    () => window.matchMedia(SLA_DESKTOP_MEDIA_QUERY).matches,
  )

  useEffect(() => {
    const media = window.matchMedia(SLA_DESKTOP_MEDIA_QUERY)
    const update = (event: MediaQueryListEvent) => setIsDesktop(event.matches)
    setIsDesktop(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return isDesktop
}

function DesktopIssueRow({
  issue,
  expanded,
  onToggle,
  jiraBase,
}: {
  issue: SlaDashboardIssue
  expanded: boolean
  onToggle: () => void
  jiraBase: string
}) {
  return (
    <>
      <tr className="border-b border-apple-divider/60 transition-colors hover:bg-apple-gray/50">
        <td className="px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onToggle}
              aria-expanded={expanded}
              aria-label={`${issue.key} 댓글 ${expanded ? '접기' : '펼치기'}`}
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg text-apple-light transition-colors hover:bg-brand-50 hover:text-brand-600"
            >
              <ChevronDown size={16} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
            <IssueTypeIcon type={issue.type} />
            <a
              href={`${jiraBase}/browse/${issue.key}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-mono text-label font-semibold text-brand-600 hover:text-brand-700"
            >
              {issue.key}
              <ExternalLink size={12} />
            </a>
          </div>
        </td>
        <td className="max-w-md px-5 py-3.5 text-body text-apple-dark">
          <span className="block truncate" title={issue.summary}>{issue.summary || '-'}</span>
        </td>
        <td className="px-5 py-3.5 text-label tabular-nums text-apple-mid">{issue.created || '-'}</td>
        <td className="px-5 py-3.5"><StatusBadge status={issue.status} /></td>
      </tr>
      {expanded && (
        <tr className="border-b border-apple-divider/60">
          <td colSpan={4} className="px-5 py-4"><IssueCommentsPanel issueKey={issue.key} /></td>
        </tr>
      )}
    </>
  )
}

function MobileIssueCard({
  issue,
  expanded,
  onToggle,
  jiraBase,
}: {
  issue: SlaDashboardIssue
  expanded: boolean
  onToggle: () => void
  jiraBase: string
}) {
  return (
    <article className="border-b border-apple-divider/60 p-4 last:border-0">
      <div className="flex items-start gap-3">
        <IssueTypeIcon type={issue.type} />
        <a
          href={`${jiraBase}/browse/${issue.key}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-label font-semibold text-brand-600"
        >
          {issue.key}
          <ExternalLink size={12} />
        </a>
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-caption sm:grid-cols-2">
        <div className="sm:col-span-2">
          <dt className="text-apple-light">티켓 제목</dt>
          <dd className="mt-0.5 break-words text-body text-apple-dark">{issue.summary || '-'}</dd>
        </div>
        <div>
          <dt className="text-apple-light">생성일</dt>
          <dd className="mt-0.5 tabular-nums text-apple-mid">{issue.created || '-'}</dd>
        </div>
        <div>
          <dt className="text-apple-light">진행상태</dt>
          <dd className="mt-1"><StatusBadge status={issue.status} /></dd>
        </div>
      </dl>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-control font-medium text-brand-600 hover:bg-brand-50"
      >
        <ChevronDown size={15} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
        최근 댓글 {expanded ? '접기' : '펼치기'}
      </button>
      {expanded && <div className="mt-3"><IssueCommentsPanel issueKey={issue.key} /></div>}
    </article>
  )
}

export default function SlaIssueActivityTable({ issues }: { issues: SlaDashboardIssue[] }) {
  const { jiraBase } = useJira()
  const isDesktopLayout = useIsDesktopSlaLayout()
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<SortState | null>(null)
  const [collapsedKeys, setCollapsedKeys] = useState<Set<string>>(() => new Set())
  const totalPages = Math.max(1, Math.ceil(issues.length / TABLE_PAGE_SIZE))
  const sortedIssues = useMemo(() => {
    if (!sort) return issues
    return [...issues].sort((a, b) => {
      const left = a[sort.key].trim()
      const right = b[sort.key].trim()
      if (!left) return right ? 1 : 0
      if (!right) return -1
      const result = SORT_COLLATOR.compare(left, right)
      return sort.direction === 'asc' ? result : -result
    })
  }, [issues, sort])

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages))
  }, [totalPages])

  const start = (page - 1) * TABLE_PAGE_SIZE
  const pageItems = sortedIssues.slice(start, start + TABLE_PAGE_SIZE)

  const toggleSort = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction: current?.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }))
    setPage(1)
  }

  const toggleIssue = (issueKey: string) => {
    setCollapsedKeys((current) => {
      const next = new Set(current)
      if (next.has(issueKey)) next.delete(issueKey)
      else next.add(issueKey)
      return next
    })
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-apple-divider/70 bg-apple-surface shadow-apple">
      {isDesktopLayout ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] table-fixed border-collapse">
            <colgroup>
              <col className="w-[18%]" />
              <col className="w-[44%]" />
              <col className="w-[22%]" />
              <col className="w-[16%]" />
            </colgroup>
            <thead className="bg-apple-gray/70">
              <tr className="border-b border-apple-divider/70">
                {SORT_COLUMNS.map(({ key, label }) => {
                  const direction = sort?.key === key ? sort.direction : null
                  const nextDirection = direction === 'asc' ? '내림차순' : '오름차순'
                  const SortIcon = direction === 'asc' ? ArrowUp : direction === 'desc' ? ArrowDown : ArrowUpDown
                  return (
                    <th
                      key={key}
                      scope="col"
                      aria-sort={direction === 'asc' ? 'ascending' : direction === 'desc' ? 'descending' : 'none'}
                      className="text-left text-label font-semibold text-apple-light"
                    >
                      <button
                        type="button"
                        onClick={() => toggleSort(key)}
                        aria-label={`${label} ${nextDirection} 정렬`}
                        title={`${label} ${nextDirection} 정렬`}
                        className={`flex w-full items-center gap-1.5 px-5 py-3 text-left transition-colors hover:bg-apple-divider/40 hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 ${direction ? 'text-brand-600' : ''}`}
                      >
                        {label}
                        <SortIcon size={13} aria-hidden="true" className={`shrink-0 ${direction ? '' : 'opacity-50'}`} />
                      </button>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {pageItems.map((issue) => (
                <DesktopIssueRow
                  key={issue.key}
                  issue={issue}
                  expanded={!collapsedKeys.has(issue.key)}
                  onToggle={() => toggleIssue(issue.key)}
                  jiraBase={jiraBase}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="divide-y divide-apple-divider/40">
          {pageItems.map((issue) => (
            <MobileIssueCard
              key={issue.key}
              issue={issue}
              expanded={!collapsedKeys.has(issue.key)}
              onToggle={() => toggleIssue(issue.key)}
              jiraBase={jiraBase}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider/70 px-4 py-3 md:px-5">
          <span className="text-caption text-apple-light">
            {start + 1}–{Math.min(start + TABLE_PAGE_SIZE, issues.length)} / {issues.length}건
          </span>
          <div className="flex flex-wrap gap-1">
            {Array.from({ length: totalPages }).map((_, index) => {
              const pageNumber = index + 1
              return (
                <button
                  key={pageNumber}
                  type="button"
                  onClick={() => setPage(pageNumber)}
                  className={`min-w-8 rounded-lg px-2.5 py-1 text-control font-medium transition-colors ${
                    page === pageNumber
                      ? 'bg-brand-600 text-white'
                      : 'bg-apple-gray text-apple-mid hover:bg-apple-divider/70'
                  }`}
                >
                  {pageNumber}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
