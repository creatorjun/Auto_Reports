// frontend/src/presentation/components/layout/Header.tsx
import { useUiStore } from '@/app/store/uiStore'
import TriggerButton from '../common/TriggerButton'

export default function Header() {
  const { triggerMessage } = useUiStore()
  return (
    <header className="bg-white/80 backdrop-blur-xl border-b border-apple-divider/80 px-7 py-0 h-14 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1.2" fill="white" />
              <rect x="8" y="1" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="1" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="8" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.4" />
            </svg>
          </div>
          <span className="text-[15px] font-semibold text-apple-dark tracking-tight">TAC Auto Reports</span>
        </div>
        {triggerMessage && (
          <span className="text-xs text-green-700 bg-green-50 border border-green-200/60 px-2.5 py-1 rounded-full font-medium">
            {triggerMessage}
          </span>
        )}
      </div>
      <TriggerButton />
    </header>
  )
}
