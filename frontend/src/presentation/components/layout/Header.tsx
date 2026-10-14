// frontend/src/presentation/components/layout/Header.tsx
import { useEffect, useCallback } from 'react'
import seculayerLogo from '@/assets/seculayer-logo.png'
import { useReportStore } from '@/presentation/state/reportStore'
import { useUiStore } from '@/presentation/state/uiStore'
import { useRefreshReport } from '@/presentation/hooks/useReport'
import SearchWidget from '@/presentation/components/common/SearchWidget'
import RefreshButton from '@/presentation/components/common/RefreshButton'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const { triggerMessage } = useUiStore()
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

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.ctrlKey && !e.shiftKey && !e.altKey && e.key === 'r') {
      e.preventDefault()
      e.stopPropagation()
      e.stopImmediatePropagation()
      if (!currentReport || currentReport.scope !== 'standard' || isTriggerLoading || isPending) return
      setTriggerLoading(true)
      setTriggerMessage(null)
      mutate()
    }
  }, [currentReport, isTriggerLoading, isPending, mutate, setTriggerLoading, setTriggerMessage])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [handleKeyDown])

  return (
    <header className="bg-apple-surface flex-shrink-0 border-b border-apple-divider/60">
      <div className="flex flex-col xl:hidden">
        <div className="relative flex items-center justify-center px-4 pt-3 pb-1">
          <div className="flex items-center gap-2">
            <img src={seculayerLogo} alt="" className="w-7 h-7 object-contain flex-shrink-0" />
            <span className="text-[17px] font-bold text-apple-dark tracking-tight">SecuLayer</span>
          </div>
          <div className="absolute right-4 top-2.5">
            <ThemeToggle collapsed />
          </div>
        </div>
        {triggerMessage && (
          <p className="text-center text-[11px] text-green-700 pb-0.5 px-4 truncate">{triggerMessage}</p>
        )}
        <div className="flex items-center gap-2 px-4 pb-2.5 pt-1 overflow-hidden">
          {currentReport && (
            <div className="flex items-center gap-2 flex-shrink-0">
              {currentReport.scope === 'standard' && <RefreshButton />}
              <p className="text-[11px] text-apple-light tabular-nums truncate max-w-[160px]">
                {currentReport.week_start} – {currentReport.week_end}
              </p>
            </div>
          )}
          <div className="ml-auto flex-shrink-0">
            <SearchWidget />
          </div>
        </div>
      </div>

      <div className="hidden h-14 items-center justify-between px-4 xl:flex 3xl:h-16">
        <div className="w-[28rem] 3xl:w-[32rem] flex items-center gap-3 overflow-hidden">
          {currentReport && (
            <>
              {currentReport.scope === 'standard' && (
                <div className="flex-shrink-0">
                  <RefreshButton />
                </div>
              )}
              <p className="hidden sm:block text-ui-xs 3xl:text-ui-sm text-apple-light tabular-nums truncate">
                {currentReport.week_start} – {currentReport.week_end}
              </p>
            </>
          )}
        </div>

        <div className="flex flex-col items-center justify-center gap-0.5 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <img src={seculayerLogo} alt="" className="w-8 h-8 3xl:w-10 3xl:h-10 object-contain flex-shrink-0" />
            <span className="text-[20px] 3xl:text-[24px] font-bold text-apple-dark tracking-tight">SecuLayer</span>
          </div>
          {triggerMessage && (
            <span className="text-[11px] 3xl:text-[12px] text-green-700 max-w-[260px] truncate">{triggerMessage}</span>
          )}
        </div>

        <div className="flex-shrink-0">
          <SearchWidget />
        </div>
      </div>
    </header>
  )
}
