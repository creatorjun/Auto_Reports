// frontend/src/presentation/components/layout/Header.tsx
import seculayerLogo from '@/assets/seculayer-logo.png'
import { useReportStore } from '@/presentation/state/reportStore'
import { useUiStore } from '@/presentation/state/uiStore'
import SearchWidget from '@/presentation/components/common/SearchWidget'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const { triggerMessage } = useUiStore()
  const { currentReport } = useReportStore()

  return (
    <header className="bg-apple-surface flex-shrink-0 border-b border-apple-divider/60">
      <div className="flex flex-col xl:hidden">
        <div className="relative flex items-center justify-center px-4 pt-3 pb-1">
          <div className="flex items-center gap-2">
            <img src={seculayerLogo} alt="" className="w-7 h-7 object-contain flex-shrink-0" />
            <span className="text-label font-bold text-apple-dark tracking-tight">SecuLayer</span>
          </div>
          <div className="absolute right-4 top-2.5">
            <ThemeToggle collapsed />
          </div>
        </div>
        {triggerMessage && (
          <p className="text-center text-control-label text-green-700 pb-0.5 px-4 truncate">{triggerMessage}</p>
        )}
        <div className="flex items-center gap-2 px-4 pb-2.5 pt-1 overflow-hidden">
          {currentReport && (
            <div className="flex items-center gap-2 flex-shrink-0">
              <p className="text-control-label text-apple-light tabular-nums truncate max-w-[160px]">
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
              <p className="hidden sm:block text-caption 3xl:text-label text-apple-light tabular-nums truncate">
                {currentReport.week_start} – {currentReport.week_end}
              </p>
            </>
          )}
        </div>

        <div className="flex flex-col items-center justify-center gap-0.5 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <img src={seculayerLogo} alt="" className="w-8 h-8 3xl:w-10 3xl:h-10 object-contain flex-shrink-0" />
            <span className="text-body 3xl:text-page-title font-bold text-apple-dark tracking-tight">SecuLayer</span>
          </div>
          {triggerMessage && (
            <span className="text-control-label text-green-700 max-w-[260px] truncate">{triggerMessage}</span>
          )}
        </div>

        <div className="flex-shrink-0">
          <SearchWidget />
        </div>
      </div>
    </header>
  )
}
