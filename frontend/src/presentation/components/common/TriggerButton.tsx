// frontend/src/presentation/components/common/TriggerButton.tsx
import { useTrigger } from '@/infrastructure/hooks/useTrigger'
import { useUiStore } from '@/app/store/uiStore'

export default function TriggerButton() {
  const { mutate } = useTrigger()
  const { isTriggerLoading } = useUiStore()
  return (
    <button
      onClick={() => mutate()}
      disabled={isTriggerLoading}
      className="flex items-center gap-1.5 px-4 py-1.5 bg-brand-600 hover:bg-brand-700
                 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed
                 text-white text-[13px] font-medium rounded-full transition-all duration-200
                 shadow-sm hover:shadow-md"
    >
      {isTriggerLoading ? (
        <>
          <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          <span>생성 중...</span>
        </>
      ) : (
        <>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M1 6h10" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span>보고서 생성</span>
        </>
      )}
    </button>
  )
}
