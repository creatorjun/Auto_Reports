// frontend/src/presentation/components/common/DashboardFallbacks.tsx
import LoadingSpinner from './LoadingSpinner'

export function ModalFallback() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-8 flex items-center justify-center">
        <LoadingSpinner text="로딩 중..." />
      </div>
    </div>
  )
}

export function ChartFallback() {
  return (
    <div className="flex items-center justify-center h-40 rounded-xl bg-gray-50">
      <LoadingSpinner text="" />
    </div>
  )
}
