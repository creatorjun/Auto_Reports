// frontend/src/presentation/components/common/LazyGenerateReportModal.tsx
import { lazy, Suspense } from 'react'
import LoadingSpinner from './LoadingSpinner'

const GenerateReportModal = lazy(() => import('./GenerateReportModal'))

interface Props {
  onClose: () => void
}

const ModalFallback = () => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-8 flex items-center justify-center">
      <LoadingSpinner text="로딩 중..." />
    </div>
  </div>
)

export default function LazyGenerateReportModal({ onClose }: Props) {
  return (
    <Suspense fallback={<ModalFallback />}>
      <GenerateReportModal onClose={onClose} />
    </Suspense>
  )
}
