// frontend/src/presentation/components/common/TriggerButton.tsx
import { useState } from 'react'
import { useUiStore } from '@/app/store/uiStore'
import LazyGenerateReportModal from './LazyGenerateReportModal'

export default function TriggerButton() {
  const [showModal, setShowModal]   = useState(false)
  const { isTriggerLoading, triggerMessage } = useUiStore()

  return (
    <>
      <div className="flex flex-col items-end gap-1">
        <button
          onClick={() => setShowModal(true)}
          disabled={isTriggerLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold bg-brand-600 hover:bg-brand-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-all duration-200 shadow-sm hover:shadow-md"
        >
          {isTriggerLoading ? (
            <>
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>생성 중...</span>
            </>
          ) : (
            <span>보고서 생성</span>
          )}
        </button>
        {triggerMessage && (
          <p className={`text-[11px] font-medium ${
            triggerMessage.includes('완료') ? 'text-green-600' : 'text-red-500'
          }`}>
            {triggerMessage}
          </p>
        )}
      </div>

      {showModal && <LazyGenerateReportModal onClose={() => setShowModal(false)} />}
    </>
  )
}
