// frontend/src/presentation/components/sla/SlaIssueActivityTable.tsx
import { useEffect, useState } from 'react'
import { ChevronDown, ExternalLink, MessageSquare, RefreshCw } from 'lucide-react'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import { useJira } from '@/presentation/context/JiraContext'
import { useSlaIssueComments } from '@/presentation/hooks/useSlaDashboard'
import type { SlaDashboardComment, SlaDashboardIssue } from '@/domain/SlaDashboard'

function CommentEntry({ comment }: { comment: SlaDashboardComment }) {
  const wasEdited = comment.updated && comment.updated !== comment.created
  return (
    <li className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-apple-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-apple-dark">{comment.author}</span>
        <span className="text-[12px] tabular-nums text-apple-light">
          {comment.created || '-'}
          {wasEdited && ` · 수정 ${comment.updated}`}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-6 text-apple-mid">
        {comment.body || '내용이 없는 댓글입니다.'}
      </p>
    </li>
  )
}

function CommentPanel({ issueKey }: { issueKey: string }) {
  const { data, isLoading, isError, refetch } = useSlaIssueComments(issueKey, true)

  return (
    <div className="rounded-2xl border border-brand-100 bg-brand-50/50 p-4 md:p-5">
      <div className="mb-3 flex items-center gap-2">
        <MessageSquare size={16} className="text-brand-600" />
        <h3 className="text-[13px] font-semibold text-apple-dark">최근 작성된 댓글</h3>
        <span className="text-[12px] text-apple-light">최대 5개</span>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 py-5 text-[13px] text-apple-light">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600" />
          댓글을 불러오는 중입니다.
        </div>
      )}

      {isError && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3">
          <span className="text-[13px] text-red-600">댓글을 불러오지 못했습니다.</span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-medium text-red-600 hover:bg-red-100"
          >
            <RefreshCw size={13} />
            다시 시도
          </button>
        </div>
      )}

      {!isLoading && !isError && data?.length === 0 && (
        <div className="rounded-xl bg-white px-4 py-5 text-center text-[13px] text-apple-light">
          작성된 댓글이 없습니다.
        </div>
      )}

      {data && data.length > 0 && (
        <ol className="space-y-2.5">
          {data.map((comment) => <CommentEntry key={comment.id} comment={comment} />)}
        </ol>
      )}
    </div>
  )
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
            <a
              href={`${jiraBase}/browse/${issue.key}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-mono text-[13px] font-semibold text-brand-600 hover:text-brand-700"
            >
              {issue.key}
              <ExternalLink size={12} />
            </a>
          </div>
        </td>
        <td className="px-5 py-3.5 text-[13px] tabular-nums text-apple-mid">{issue.created || '-'}</td>
        <td className="px-5 py-3.5 text-[13px] tabular-nums text-apple-mid">{issue.updated || '-'}</td>
        <td className="px-5 py-3.5"><StatusBadge status={issue.status} /></td>
      </tr>
      {expanded && (
        <tr className="border-b border-apple-divider/60">
          <td colSpan={4} className="px-5 py-4"><CommentPanel issueKey={issue.key} /></td>
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
      <div className="flex items-start justify-between gap-3">
        <a
          href={`${jiraBase}/browse/${issue.key}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-[13px] font-semibold text-brand-600"
        >
          {issue.key}
          <ExternalLink size={12} />
        </a>
        <StatusBadge status={issue.status} />
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-2 text-[12px] sm:grid-cols-2">
        <div>
          <dt className="text-apple-light">이슈 최초 생성 시간</dt>
          <dd className="mt-0.5 tabular-nums text-apple-mid">{issue.created || '-'}</dd>
        </div>
        <div>
          <dt className="text-apple-light">댓글 포함 마지막 업데이트 시간</dt>
          <dd className="mt-0.5 tabular-nums text-apple-mid">{issue.updated || '-'}</dd>
        </div>
      </dl>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] font-medium text-brand-600 hover:bg-brand-50"
      >
        <ChevronDown size={15} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
        최근 댓글 {expanded ? '접기' : '펼치기'}
      </button>
      {expanded && <div className="mt-3"><CommentPanel issueKey={issue.key} /></div>}
    </article>
  )
}

export default function SlaIssueActivityTable({ issues }: { issues: SlaDashboardIssue[] }) {
  const { jiraBase } = useJira()
  const [page, setPage] = useState(1)
  const [desktopExpanded, setDesktopExpanded] = useState<string | null>(null)
  const [mobileExpanded, setMobileExpanded] = useState<string | null>(null)
  const totalPages = Math.max(1, Math.ceil(issues.length / TABLE_PAGE_SIZE))

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages))
  }, [totalPages])

  const start = (page - 1) * TABLE_PAGE_SIZE
  const pageItems = issues.slice(start, start + TABLE_PAGE_SIZE)

  const changePage = (nextPage: number) => {
    setPage(nextPage)
    setDesktopExpanded(null)
    setMobileExpanded(null)
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-apple-divider/70 bg-white shadow-apple">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[900px] border-collapse">
          <thead className="bg-apple-gray/70">
            <tr className="border-b border-apple-divider/70">
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">티켓 번호</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">이슈 최초 생성 시간</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">댓글 포함 마지막 업데이트 시간</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">진행 상태</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((issue) => (
              <DesktopIssueRow
                key={issue.key}
                issue={issue}
                expanded={desktopExpanded === issue.key}
                onToggle={() => setDesktopExpanded((current) => current === issue.key ? null : issue.key)}
                jiraBase={jiraBase}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div className="divide-y divide-apple-divider/40 md:hidden">
        {pageItems.map((issue) => (
          <MobileIssueCard
            key={issue.key}
            issue={issue}
            expanded={mobileExpanded === issue.key}
            onToggle={() => setMobileExpanded((current) => current === issue.key ? null : issue.key)}
            jiraBase={jiraBase}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider/70 px-4 py-3 md:px-5">
          <span className="text-[12px] text-apple-light">
            {start + 1}–{Math.min(start + TABLE_PAGE_SIZE, issues.length)} / {issues.length}건
          </span>
          <div className="flex flex-wrap gap-1">
            {Array.from({ length: totalPages }).map((_, index) => {
              const pageNumber = index + 1
              return (
                <button
                  key={pageNumber}
                  type="button"
                  onClick={() => changePage(pageNumber)}
                  className={`min-w-8 rounded-lg px-2.5 py-1 text-[12px] font-medium transition-colors ${
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
