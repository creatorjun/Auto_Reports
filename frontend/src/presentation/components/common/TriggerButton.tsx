import { useTrigger } from '@/infrastructure/hooks/useTrigger'
import { useUiStore } from '@/app/store/uiStore'

export default function TriggerButton() {
  const { mutate } = useTrigger()
  const { isTriggerLoading } = useUiStore()
  return (
    <button
      onClick={() => mutate()}
      disabled={isTriggerLoading}
      className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50
                 text-white text-sm font-semibold rounded-xl transition-colors"
    >
      {isTriggerLoading
        ? <><span className="animate-spin">⌛</span> 생성 중...    </>
        : <>⚡ 보고서 지금 생성</>
      }
    </button>
  )
}
