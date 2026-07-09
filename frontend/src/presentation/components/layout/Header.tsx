// frontend/src/presentation/components/layout/Header.tsx
import { useReportStore } from '@/app/store/reportStore'
import { useUiStore } from '@/app/store/uiStore'
import SearchWidget from '@/presentation/components/common/SearchWidget'

function getWeekTitle(weekStart: string): string {
  const date = new Date(weekStart)
  const month = date.getMonth() + 1
  const firstDay = new Date(date.getFullYear(), date.getMonth(), 1)
  const week = Math.ceil((date.getDate() + firstDay.getDay()) / 7)
  return `TAC ${month}월 ${week}주차 주간보고`
}

export default function Header() {
  const { triggerMessage } = useUiStore()
  const { currentReport } = useReportStore()

  const title = currentReport?.week_start
    ? getWeekTitle(currentReport.week_start)
    : 'TAC 주간보고'

  return (
    <header className="bg-white h-14 3xl:h-16 flex items-center justify-between px-4 flex-shrink-0">
      <div className="w-[28rem] 3xl:w-[32rem] flex items-center">
        {currentReport && (
          <p className="hidden sm:block text-ui-xs 3xl:text-ui-sm text-apple-light tabular-nums">
            {currentReport.week_start} – {currentReport.week_end}
            <span className="mx-1.5 text-apple-divider">·</span>
            생성: {currentReport.report_date}
          </p>
        )}
      </div>

      <div className="flex flex-col items-center justify-center gap-0.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 3xl:w-8 3xl:h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1.2" fill="white" />
              <rect x="8" y="1" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="1" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="8" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.4" />
            </svg>
          </div>
          <span className="text-[20px] 3xl:text-[24px] font-bold text-apple-dark tracking-tight">{title}</span>
        </div>
        {triggerMessage && (
          <span className="text-[11px] 3xl:text-[12px] text-green-700">{triggerMessage}</span>
        )}
      </div>

      <SearchWidget />
    </header>
  )
}
