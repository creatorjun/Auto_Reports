// frontend/src/presentation/components/layout/Header.tsx
import { useReportStore } from '@/presentation/state/reportStore'
import { useUiStore } from '@/presentation/state/uiStore'
import BrandLogo from '@/presentation/components/common/BrandLogo'
import SearchWidget from '@/presentation/components/common/SearchWidget'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const { triggerMessage } = useUiStore()
  const { currentReport } = useReportStore()

  return (
    <header className="bg-apple-surface flex-shrink-0 border-b border-apple-divider/60">
      <div className="pointer-events-none fixed left-1/2 top-0 z-10 flex h-11 -translate-x-1/2 flex-col items-center justify-center gap-0.5 xl:h-14 3xl:h-16">
        <BrandLogo className="w-44 xl:w-48 3xl:w-56" />
        {triggerMessage && (
          <span className="hidden max-w-[260px] truncate text-control-label text-green-700 xl:block">{triggerMessage}</span>
        )}
      </div>
      <div className="flex flex-col xl:hidden">
        <div className="relative h-11">
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
        <div className="flex min-w-0 items-center gap-3 overflow-hidden">
          {currentReport && (
            <>
              <p className="hidden sm:block text-caption text-apple-light tabular-nums truncate">
                {currentReport.week_start} – {currentReport.week_end}
              </p>
            </>
          )}
        </div>

        <div className="flex-shrink-0">
          <SearchWidget />
        </div>
      </div>
    </header>
  )
}
