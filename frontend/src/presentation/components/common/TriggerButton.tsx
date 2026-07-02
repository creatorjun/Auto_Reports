// frontend/src/presentation/components/common/TriggerButton.tsx
import { useTrigger } from '@/infrastructure/hooks/useTrigger'
import { useUiStore } from '@/app/store/uiStore'

interface Props {
  collapsed?: boolean
}

export default function TriggerButton({ collapsed = false }: Props) {
  const { mutate } = useTrigger()
  const { isTriggerLoading } = useUiStore()

  if (collapsed) {
    return (
      <button
        onClick={() => mutate()}
        disabled={isTriggerLoading}
        title="보고서 생성"
        className="w-10 h-10 flex items-center justify-center rounded-xl
                   bg-brand-600 hover:bg-brand-700 active:scale-95
                   disabled:opacity-40 disabled:cursor-not-allowed
                   text-white transition-all duration-200 shadow-sm hover:shadow-md"
      >
        {isTriggerLoading ? (
          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        )}
      </button>
    )
  }

  return (
    <button
      onClick={() => mutate()}
      disabled={isTriggerLoading}
      className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                 bg-brand-600 hover:bg-brand-700 active:scale-95
                 disabled:opacity-40 disabled:cursor-not-allowed
                 text-white text-[13px] font-medium rounded-xl
                 transition-all duration-200 shadow-sm hover:shadow-md"
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
