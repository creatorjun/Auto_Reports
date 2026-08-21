// frontend/src/presentation/pages/SlaDashboardPage.tsx
import { RefreshCw } from 'lucide-react'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import SlaIssueActivityTable from '@/presentation/components/sla/SlaIssueActivityTable'
import { useSlaDashboardIssues } from '@/presentation/hooks/useSlaDashboard'

export default function SlaDashboardPage() {
  const { data: issues = [], isLoading, isError, refetch } = useSlaDashboardIssues()

  if (isLoading) return <LoadingSpinner text="SLA 대시보드 로딩 중..." />

  return (
    <div className="mx-auto w-full max-w-content space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-apple-dark">SLA 대시보드</h1>
        <p className="mt-1 text-[13px] text-apple-light">
          최근 이슈 현황 기반 · 최신 {issues.length}건
        </p>
      </div>

      {isError && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200/70 bg-red-50 px-5 py-4">
          <span className="text-[13px] text-red-600">최근 이슈 현황을 불러오지 못했습니다.</span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-medium text-red-600 hover:bg-red-100"
          >
            <RefreshCw size={14} />
            다시 시도
          </button>
        </div>
      )}

      {!isError && issues.length === 0 && (
        <div className="card py-16 text-center text-[13px] text-apple-light">
          최근 이슈 현황 데이터가 없습니다.
        </div>
      )}

      {!isError && issues.length > 0 && <SlaIssueActivityTable issues={issues} />}
    </div>
  )
}
