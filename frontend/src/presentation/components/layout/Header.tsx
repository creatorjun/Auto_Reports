import { useUiStore } from '@/app/store/uiStore'
import TriggerButton from '../common/TriggerButton'

export default function Header() {
  const { triggerMessage } = useUiStore()
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold text-brand-700">📊 TAC Auto Reports</span>
        {triggerMessage && (
          <span className="text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
            ✅ {triggerMessage}
          </span>
        )}
      </div>
      <TriggerButton />
    </header>
  )
}
