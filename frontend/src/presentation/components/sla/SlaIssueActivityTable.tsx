// frontend/src/presentation/components/sla/SlaIssueActivityTable.tsx
import { useEffect, useState } from 'react'
import { ChevronDown, ExternalLink, MessageSquare, RefreshCw } from 'lucide-react'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { IssueTypeIcon } from '@/presentation/components/common/IssueTypeIcon'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import { useJira } from '@/presentation/context/JiraContext'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useSlaIssueComments } from '@/presentation/hooks/useSlaDashboard'
import type {
  SlaDashboardComment,
  SlaDashboardCommentImage,
  SlaDashboardIssue,
} from '@/domain/SlaDashboard'

function CommentImage({
  issueKey,
  commentId,
  image,
}: {
  issueKey: string
  commentId: string
  image: SlaDashboardCommentImage
}) {
  const { slaDashboard } = useApplicationServices()
  const [source, setSource] = useState('')
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl = ''
    setSource('')
    setFailed(false)
    slaDashboard.getCommentImage(issueKey, commentId, image.attachment_id)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setSource(objectUrl)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [commentId, image.attachment_id, issueKey, slaDashboard])

  if (failed) {
    return (
      <div className="flex min-h-24 items-center justify-center rounded-xl border border-red-100 bg-red-50 px-4 text-[12px] text-red-600">
        이미지를 불러오지 못했습니다.
      </div>
    )
  }

  if (!source) {
    return <div className="min-h-32 animate-pulse rounded-xl bg-apple-gray" aria-label="댓글 이미지 로딩 중" />
  }

  return (
    <a href={source} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl bg-apple-gray">
      <img
        src={source}
        alt={image.alt || '댓글 첨부 이미지'}
        loading="lazy"
        className="max-h-[32rem] w-full object-contain"
      />
    </a>
  )
}

function CommentEntry({ issueKey, comment }: { issueKey: string; comment: SlaDashboardComment }) {
  const wasEdited = comment.updated && comment.updated !== comment.created
  return (
    <li className="rounded-xl border border-apple-divider/70 bg-apple-surface px-4 py-3 shadow-apple-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-apple-dark">{comment.author}</span>
        <span className="text-[12px] tabular-nums text-apple-light">
          {comment.created || '-'}
          {wasEdited && ` · 수정 ${comment.updated}`}
        </span>
      </div>
      {comment.body && (
        <p className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-6 text-apple-mid">
          {comment.body}
        </p>
      )}
      {!comment.body && comment.images.length === 0 && (
        <p className="mt-2 text-[13px] text-apple-light">내용이 없는 댓글입니다.</p>
      )}
      {comment.images.length > 0 && (
        <div className="mt-3 grid min-w-0 grid-cols-1 gap-3 2xl:grid-cols-2">
          {comment.images.map((image) => (
            <CommentImage
              key={image.attachment_id}
              issueKey={issueKey}
              commentId={comment.id}
              image={image}
            />
          ))}
        </div>
      )}
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
        <div className="rounded-xl bg-apple-surface px-4 py-5 text-center text-[13px] text-apple-light">
          작성된 댓글이 없습니다.
        </div>
      )}

      {data && data.length > 0 && (
        <ol className="space-y-2.5">
          {data.map((comment) => <CommentEntry key={comment.id} issueKey={issueKey} comment={comment} />)}
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
            <IssueTypeIcon type={issue.type} />
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
        <td className="max-w-md px-5 py-3.5 text-[13px] text-apple-dark">
          <span className="block truncate" title={issue.summary}>{issue.summary || '-'}</span>
        </td>
        <td className="px-5 py-3.5 text-[13px] tabular-nums text-apple-mid">{issue.created || '-'}</td>
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
      <div className="flex items-start gap-3">
        <IssueTypeIcon type={issue.type} />
        <a
          href={`${jiraBase}/browse/${issue.key}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-[13px] font-semibold text-brand-600"
        >
          {issue.key}
          <ExternalLink size={12} />
        </a>
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-[12px] sm:grid-cols-2">
        <div className="sm:col-span-2">
          <dt className="text-apple-light">티켓 제목</dt>
          <dd className="mt-0.5 break-words text-[13px] text-apple-dark">{issue.summary || '-'}</dd>
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
  const [collapsedKeys, setCollapsedKeys] = useState<Set<string>>(() => new Set())
  const totalPages = Math.max(1, Math.ceil(issues.length / TABLE_PAGE_SIZE))

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages))
  }, [totalPages])

  const start = (page - 1) * TABLE_PAGE_SIZE
  const pageItems = issues.slice(start, start + TABLE_PAGE_SIZE)

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
      <div className="hidden overflow-x-auto xl:block">
        <table className="w-full min-w-[900px] border-collapse">
          <thead className="bg-apple-gray/70">
            <tr className="border-b border-apple-divider/70">
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">티켓 번호</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">티켓 제목</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">생성일</th>
              <th className="px-5 py-3 text-left text-[12px] font-semibold text-apple-light">진행상태</th>
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

      <div className="divide-y divide-apple-divider/40 xl:hidden">
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
                  onClick={() => setPage(pageNumber)}
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
