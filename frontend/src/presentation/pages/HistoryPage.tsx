// frontend/src/presentation/pages/HistoryPage.tsx
import { useState } from 'react'
import { useAllReports, useDeleteReport } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { HistoryReportTable } from '@/presentation/components/tables/HistoryReportTable'
import DeleteConfirmModal from '@/presentation/components/common/DeleteConfirmModal'

const PAGE_SIZE = 20

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
        <HistoryReportTable data={data ?? []} onDelete={setConfirmId} />
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
