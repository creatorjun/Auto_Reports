// frontend/src/presentation/components/common/IssueCommentsPanel.tsx
import { useEffect, useState } from 'react'
import { ChevronDown, MessageSquare, RefreshCw } from 'lucide-react'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useSlaIssueComments } from '@/presentation/hooks/useSlaDashboard'
import type { BinaryObjectUrl } from '@/application/ports/ApplicationServices'
import type { SlaDashboardComment, SlaDashboardCommentImage } from '@/domain/SlaDashboard'

function CommentImage({
  issueKey,
  commentId,
  image,
  reportId,
}: {
  issueKey: string
  commentId: string
  image: SlaDashboardCommentImage
  reportId?: number
}) {
  const { slaDashboard } = useApplicationServices()
  const [source, setSource] = useState('')
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl: BinaryObjectUrl | null = null
    setSource('')
    setFailed(false)
    slaDashboard.getCommentImage(issueKey, commentId, image.attachment_id, reportId)
      .then((content) => {
        if (!active) return
        objectUrl = content.createObjectUrl()
        setSource(objectUrl.url)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
      objectUrl?.close()
    }
  }, [commentId, image.attachment_id, issueKey, reportId, slaDashboard])

  if (failed) {
    return (
      <div className="flex min-h-20 max-w-full items-center rounded-xl border border-red-100 bg-red-50 px-4 text-caption text-red-600">
        이미지를 불러오지 못했습니다.
      </div>
    )
  }

  if (!source) {
    return <div className="h-24 w-48 max-w-full animate-pulse rounded-xl bg-apple-gray" aria-label="댓글 이미지 로딩 중" />
  }

  return (
    <a href={source} target="_blank" rel="noreferrer" className="inline-flex max-w-full items-start overflow-hidden rounded-xl border border-apple-divider/70">
      <img
        src={source}
        alt={image.alt || '댓글 첨부 이미지'}
        loading="lazy"
        className="block h-auto max-h-[24rem] w-auto max-w-full object-contain object-left-top"
      />
    </a>
  )
}

function CommentEntry({ issueKey, comment, reportId }: { issueKey: string; comment: SlaDashboardComment; reportId?: number }) {
  const wasEdited = comment.updated && comment.updated !== comment.created
  return (
    <li className="min-w-0 rounded-xl border border-apple-divider/70 bg-apple-surface px-4 py-3 text-left shadow-apple-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-label font-semibold text-apple-dark">{comment.author}</span>
        <span className="text-caption tabular-nums text-apple-light">
          {comment.created || '-'}
          {wasEdited && ` · 수정 ${comment.updated}`}
        </span>
      </div>
      {comment.body && (
        <p className="mt-2 whitespace-pre-wrap text-body leading-relaxed text-apple-dark [overflow-wrap:anywhere]">
          {comment.body}
        </p>
      )}
      {!comment.body && comment.images.length === 0 && (
        <p className="mt-2 text-label text-apple-light">내용이 없는 댓글입니다.</p>
      )}
      {comment.images.length > 0 && (
        <div className="mt-3 flex min-w-0 flex-col items-start gap-3">
          {comment.images.map((image) => (
            <CommentImage
              key={image.attachment_id}
              issueKey={issueKey}
              commentId={comment.id}
              image={image}
              reportId={reportId}
            />
          ))}
        </div>
      )}
    </li>
  )
}

export default function IssueCommentsPanel({ issueKey, reportId }: { issueKey: string; reportId?: number }) {
  const {
    data,
    isLoading,
    isError,
    isFetching,
    isFetchingNextPage,
    isFetchNextPageError,
    hasNextPage,
    fetchNextPage,
    refetch,
  } = useSlaIssueComments(issueKey, true, reportId)

  return (
    <div className="min-w-0 rounded-2xl border border-brand-100 bg-brand-50/50 p-4 md:p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <MessageSquare size={16} className="text-brand-600" />
        <h3 className="text-section-title font-semibold text-apple-dark">최근 작성된 댓글</h3>
        <span aria-live="polite" className="text-caption text-apple-light">{data ? `최신 ${data.length}개 · 최신순` : '최신 5개부터 표시'}</span>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 py-5 text-label text-apple-light">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600" />
          댓글을 불러오는 중입니다.
        </div>
      )}

      {isError && !isFetchNextPageError && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3">
          <span className="text-label text-red-600">댓글을 불러오지 못했습니다.</span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-control font-medium text-red-600 hover:bg-red-100"
          >
            <RefreshCw size={13} />
            다시 시도
          </button>
        </div>
      )}

      {!isLoading && !isError && data?.length === 0 && (
        <div className="rounded-xl bg-apple-surface px-4 py-5 text-center text-label text-apple-light">
          작성된 댓글이 없습니다.
        </div>
      )}

      {data && data.length > 0 && (
        <ol className="space-y-2.5">
          {data.map((comment) => <CommentEntry key={comment.id} issueKey={issueKey} comment={comment} reportId={reportId} />)}
        </ol>
      )}

      {isFetchNextPageError && (
        <p role="alert" className="mt-3 text-label text-red-600">
          댓글을 더 불러오지 못했습니다. 다시 시도해 주세요.
        </p>
      )}

      {hasNextPage && (
        <button
          type="button"
          onClick={() => void fetchNextPage({ cancelRefetch: false })}
          disabled={isFetching}
          aria-busy={isFetchingNextPage}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-brand-200 bg-apple-surface px-4 py-2.5 text-control font-medium text-brand-600 transition-colors hover:bg-brand-50 disabled:cursor-wait disabled:opacity-60"
        >
          {isFetchingNextPage ? (
            <>
              <RefreshCw size={14} className="animate-spin" />
              댓글을 불러오는 중입니다.
            </>
          ) : isFetchNextPageError ? (
            <>
              <RefreshCw size={14} />
              다시 시도
            </>
          ) : (
            <>
              <ChevronDown size={14} />
              댓글 더보기 · 최신 {(data?.length ?? 0) + 5}개
            </>
          )}
        </button>
      )}
    </div>
  )
}
