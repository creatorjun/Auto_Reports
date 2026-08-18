// frontend/src/presentation/components/common/LazyGenerateReportModal.tsx
import GenerateReportModal from './GenerateReportModal'

interface Props {
  onClose: () => void
}

export default function LazyGenerateReportModal({ onClose }: Props) {
  return <GenerateReportModal onClose={onClose} />
}
