// frontend/src/presentation/components/common/RefreshButton.tsx
import { useReportStore } from '@/app/store/reportStore'
import { useUiStore } from '@/app/store/uiStore'
import { useRefreshReport } from '@/infrastructure/hooks/useReport'

export default function RefreshButton() {
  const { currentReport } = useReportStore()
  const { isTriggerLoading, setTriggerLoading, setTriggerMessage } = useUiStore()

  const { mutate, isPending } = useRefreshReport({
    onComplete: (reportId) => {
      setTriggerLoading(false)
      setTriggerMessage(`새로고침 완료 (ID: ${reportId})`)
    },
    onError: (message) => {
      setTriggerLoading(false)
      setTriggerMessage(`새로고침 실패: ${message}`)
    },
    onTimeout: () => {
      setTriggerLoading(false)
      setTriggerMessage('새로고침이 시간 초과되었습니다.')
    },
  })

  if (!currentReport) return null

  const isDisabled = isTriggerLoading || isPending

  function handleRefresh() {
    setTriggerLoading(true)
    setTriggerMessage(null)
    mutate()
  }

  return (
    <button
      onClick={handleRefresh}
      disabled={isDisabled}
      title="최근 7일 기준 새 보고서 생성"
      className="inline-flex items-center justify-center gap-1.5
                 min-w-[88px] h-[28px] px-3
                 rounded-lg border border-apple-divider
                 text-[12px] font-medium text-apple-dark
                 hover:border-brand-400 hover:text-brand-600 hover:bg-brand-50
                 disabled:opacity-40 disabled:cursor-not-allowed
                 transition-colors duration-200"
    >
      <span className="flex-shrink-0 w-3 h-3 flex items-center justify-center">
        {isDisabled ? (
          <span className="block w-3 h-3 border-2 border-brand-300 border-t-brand-600 rounded-full animate-spin" />
        ) : (
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <path
              d="M11 6.5A4.5 4.5 0 1 1 6.5 2a4.48 4.48 0 0 1 3.18 1.32M9.68 1v2.32H12"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </span>
      <span className="whitespace-nowrap">
        {isDisabled ? '새로고침 중...' : '새로고침'}
      </span>
    </button>
  )
}
