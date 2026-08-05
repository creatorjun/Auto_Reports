// frontend/src/presentation/pages/HistoryPage.tsx
import { useState } from 'react'
import { useAllReports, useDeleteReport } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import HistoryDeleteConfirmModal from '@/presentation/components/history/HistoryDeleteConfirmModal'
import { ReportRow, MobileReportRow } from '@/presentation/components/history/HistoryReportTable'

const PAGE_SIZE = 20

export default function HistoryPage() {
  const [page, setPage] = useState(0)
  const { data, isLoading, isFetching } = useAllReports(page, PAGE_SIZE)
  const { mutate: deleteReport, isPending } = useDeleteReport()
  const [confirmId, setConfirmId] = useState<number | null>(null)

  const confirmRange = confirmId != null
    ? (data ?? []).find(r => r.id === confirmId)
    : undefined
  const rangeStr = confirmRange
    ? `${confirmRange.week_start} – ${confirmRange.week_end}`
    : ''

  const hasPrev = page > 0
  const hasNext = (data?.length ?? 0) >= PAGE_SIZE

  const handleConfirmDelete = () => {
    if (confirmId == null) return
    deleteReport(confirmId, { onSuccess: () => setConfirmId(null) })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 px-6 py-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-apple-dark">보고서 히스토리</h1>
        {isFetching && <LoadingSpinner />}
      </div>

      <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-apple-divider bg-apple-gray/40">
                <th className="px-6 py-3 3xl:px-8 text-left text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wide">ID</th>
                <th className="px-6 py-3 3xl:px-8 text-left text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wide">기간</th>
                <th className="px-6 py-3 3xl:px-8 text-left text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wide">생성일</th>
                <th className="px-6 py-3 3xl:px-8 text-left text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wide">상태</th>
                <th className="px-6 py-3 3xl:px-8 text-right text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wide">액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-divider/40">
              {(data ?? []).map((r) => (
                <ReportRow key={r.id} r={r} onDelete={setConfirmId} />
              ))}
            </tbody>
          </table>
        </div>

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

      {confirmId != null && (
        <HistoryDeleteConfirmModal
          id={confirmId}
          range={rangeStr}
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmId(null)}
          isPending={isPending}
        />
      )}
    </div>
  )
}
