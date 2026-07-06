// frontend/src/presentation/pages/HistoryPage.tsx
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAllReports, useDeleteReport } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import type { ReportSummary } from '@/domain/Report'

const PAGE_SIZE = 20

const sentimentLabel: Record<string, string> = {
  good: 'badge-good', warning: 'badge-warning', critical: 'badge-critical'
}
const sentimentText: Record<string, string> = {
  good: '양호', warning: '주의', critical: '경고'
}

function DeleteConfirmModal({ id, range, onConfirm, onCancel, isPending }: {
  id: number
  range: string
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-[320px] md:w-[380px] mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3.75v5.5M9 11.75v.5" stroke="#ef4444" strokeWidth="1.6" strokeLinecap="round"/>
              <path d="M7.273 2.5h3.454c.28 0 .537.15.674.393l4.925 8.625A.75.75 0 0 1 15.652 12.5H2.348a.75.75 0 0 1-.674-1.082l4.925-8.625A.75.75 0 0 1 7.273 2.5Z" stroke="#ef4444" strokeWidth="1.4" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-apple-dark">보고서 삭제</p>
            <p className="text-[12px] text-apple-light mt-0.5">#{id} · {range}</p>
          </div>
        </div>
        <p className="text-[13px] text-apple-dark/80 mb-5 leading-relaxed">
          이 보고서를 삭제하면 복구할 수 없습니다.<br />정말 삭제하시겠습니까?
        </p>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5"
          >
            {isPending ? (
              <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12"/>
              </svg>
            ) : null}
            삭제
          </button>
        </div>
      </div>
    </div>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 3.5h10M5.5 3.5V2.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M11.5 3.5l-.6 7.2a1 1 0 0 1-1 .8H4.1a1 1 0 0 1-1-.8L2.5 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5.5 6.5v3M8.5 6.5v3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  )
}

function ReportRow({ r, onDelete }: { r: ReportSummary; onDelete: (id: number) => void }) {
  const formattedDate = useMemo(
    () => format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko }),
    [r.created_at]
  )
  return (
    <tr className="hover:bg-apple-gray/60 transition-colors duration-150">
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[12px] 3xl:text-[13px] font-mono text-apple-light">#{r.id}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-dark">{r.week_start} – {r.week_end}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums">{formattedDate}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        {r.sentiment
          ? <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>
          : <span className="text-apple-divider text-[12px]">—</span>
        }
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-3">
          <Link
            to={`/reports/${r.id}`}
            className="text-[12px] 3xl:text-[13px] text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            상세 보기
          </Link>
          <button
            onClick={() => onDelete(r.id)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
            title="삭제"
          >
            <TrashIcon />
          </button>
        </div>
      </td>
    </tr>
  )
}

function MobileReportRow({ r, onDelete }: { r: ReportSummary; onDelete: (id: number) => void }) {
  const formattedDate = useMemo(
    () => format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko }),
    [r.created_at]
  )
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <Link to={`/reports/${r.id}`} className="flex flex-col gap-1 flex-1 min-w-0">
        <span className="text-[13px] font-medium text-apple-dark">{r.week_start} – {r.week_end}</span>
        <span className="text-[11px] text-apple-light tabular-nums">#{r.id} · {formattedDate}</span>
      </Link>
      <div className="flex items-center gap-2 flex-shrink-0">
        {r.sentiment && <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>}
        <Link to={`/reports/${r.id}`}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-apple-light">
            <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
        <button
          onClick={() => onDelete(r.id)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  )
}

export default function HistoryPage() {
  const [page, setPage] = useState(0)
  const { data, isLoading, isFetching } = useAllReports(page, PAGE_SIZE)
  const { mutate: deleteReport, isPending } = useDeleteReport()
  const [confirmId, setConfirmId] = useState<number | null>(null)

  const confirmTarget = data?.find(r => r.id === confirmId)

  const handleDelete = () => {
    if (confirmId == null) return
    deleteReport(confirmId, { onSuccess: () => setConfirmId(null) })
  }

  const hasPrev = page > 0
  const hasNext = (data?.length ?? 0) === PAGE_SIZE

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4 md:space-y-5 3xl:space-y-7">
      {confirmId != null && confirmTarget && (
        <DeleteConfirmModal
          id={confirmTarget.id}
          range={`${confirmTarget.week_start} – ${confirmTarget.week_end}`}
          onConfirm={handleDelete}
          onCancel={() => setConfirmId(null)}
          isPending={isPending}
        />
      )}

      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[18px] md:text-[22px] 3xl:text-[26px] font-semibold text-apple-dark tracking-tight">보고서 히스토리</h1>
          <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">자동 생성된 TAC 주간 보고서 목록</p>
        </div>
        {isFetching && !isLoading && (
          <span className="text-[11px] text-apple-light">업데이트 중...</span>
        )}
      </div>

      <div className={`card overflow-hidden p-0 transition-opacity duration-200 ${isFetching ? 'opacity-70' : 'opacity-100'}`}>
        {/* 데스크톱 테이블 */}
        <div className="hidden md:block">
          <table className="w-full">
            <thead className="border-b border-apple-divider/60">
              <tr>
                {['ID', '데이터 범위', '생성 시각', 'AI 상태', ''].map((h, i) => (
                  <th key={i} className="text-left px-6 py-3.5 3xl:px-8 3xl:py-4 text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-divider/40">
              {(data ?? []).map((r) => (
                <ReportRow key={r.id} r={r} onDelete={setConfirmId} />
              ))}
            </tbody>
          </table>
        </div>

        {/* 모바일 */}
        <div className="md:hidden divide-y divide-apple-divider/40">
          {(data ?? []).map((r) => (
            <MobileReportRow key={r.id} r={r} onDelete={setConfirmId} />
          ))}
        </div>

        {!data?.length && <p className="text-center text-[13px] text-apple-light py-16">보고서가 없습니다.</p>}
      </div>

      {(hasPrev || hasNext) && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage(p => p - 1)}
            disabled={!hasPrev || isFetching}
            className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ← 이전
          </button>
          <span className="text-[12px] text-apple-light">{page + 1} 페이지</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={!hasNext || isFetching}
            className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            다음 →
          </button>
        </div>
      )}
    </div>
  )
}
