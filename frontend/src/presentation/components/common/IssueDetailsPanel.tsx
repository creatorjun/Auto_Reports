// frontend/src/presentation/components/common/IssueDetailsPanel.tsx
import { useEffect, useState } from 'react'
import { FileText, RefreshCw } from 'lucide-react'
import type { BinaryObjectUrl } from '@/application/ports/ApplicationServices'
import type { SlaDashboardDescription } from '@/domain/SlaDashboard'
import { useIssueContentGateway, useIssueDescription, type IssueContentSource } from '@/presentation/hooks/useIssueContent'
import IssueCommentsPanel from './IssueCommentsPanel'

function DescriptionImage({ issueKey, reportId, source: contentSource, image }: {
  issueKey: string
  reportId?: number
  source?: IssueContentSource
  image: SlaDashboardDescription['images'][number]
}) {
  const gateway = useIssueContentGateway(reportId, contentSource)
  const [source, setSource] = useState('')
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    let objectUrl: BinaryObjectUrl | null = null
    setSource('')
    setFailed(false)
    gateway.getDescriptionImage(issueKey, image.attachment_id, controller.signal)
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
      controller.abort()
      objectUrl?.close()
    }
  }, [attempt, image.attachment_id, issueKey, gateway])

  if (failed) {
    return (
      <div role="alert" className="flex max-w-full flex-wrap items-center gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3">
        <span className="text-label text-red-600">본문 이미지를 불러오지 못했습니다.</span>
        <button
          type="button"
          onClick={() => setAttempt((value) => value + 1)}
          className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-control font-medium text-red-600 hover:bg-red-100"
        >
          <RefreshCw size={13} />
          이미지 다시 시도
        </button>
      </div>
    )
  }

  if (!source) {
    return <div className="h-24 w-48 max-w-full animate-pulse rounded-xl bg-apple-gray" aria-label="본문 이미지 로딩 중" />
  }

  return (
    <a href={source} target="_blank" rel="noreferrer" className="inline-flex max-w-full items-start overflow-hidden rounded-xl border border-apple-divider/70">
      <img
        src={source}
        alt={image.alt || '본문 첨부 이미지'}
        loading="lazy"
        onError={() => setFailed(true)}
        className="block h-auto max-h-[24rem] w-auto max-w-full object-contain object-left-top"
      />
    </a>
  )
}

export default function IssueDetailsPanel({ issueKey, reportId, source }: { issueKey: string; reportId?: number; source?: IssueContentSource }) {
  const { data, isLoading, isError, isFetching, refetch } = useIssueDescription(issueKey, reportId, source)

  return (
    <div className="min-w-0 space-y-4">
      <section className="min-w-0 rounded-2xl border border-apple-divider/70 bg-apple-surface p-4 text-left md:p-5">
        <div className="mb-3 flex items-center gap-2">
          <FileText size={16} className="text-brand-600" />
          <h3 className="text-section-title font-semibold text-apple-dark">본문</h3>
        </div>
        {isLoading && (
          <p role="status" className="flex items-center gap-2 py-5 text-label text-apple-light">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600" />
            본문을 불러오는 중입니다.
          </p>
        )}
        {isError && (
          <div role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3">
            <span className="text-label text-red-600">본문을 불러오지 못했습니다.</span>
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-control font-medium text-red-600 hover:bg-red-100 disabled:cursor-wait disabled:opacity-60"
            >
              <RefreshCw size={13} className={isFetching ? 'animate-spin' : ''} />
              본문 다시 시도
            </button>
          </div>
        )}
        {data && (
          <>
            {data.body.trim() && (
              <p className="whitespace-pre-wrap text-body leading-relaxed text-apple-dark [overflow-wrap:anywhere]">{data.body}</p>
            )}
            {!data.body.trim() && data.images.length === 0 && (
              <p className="py-4 text-label text-apple-light">작성된 본문이 없습니다.</p>
            )}
            {data.images.length > 0 && (
              <div className="mt-3 flex min-w-0 flex-col items-start gap-3">
                {data.images.map((image) => (
                  <DescriptionImage key={`${source}:${reportId}:${issueKey}:${image.attachment_id}`} issueKey={issueKey} reportId={reportId} source={source} image={image} />
                ))}
              </div>
            )}
          </>
        )}
      </section>
      <IssueCommentsPanel issueKey={issueKey} reportId={reportId} source={source} />
    </div>
  )
}
