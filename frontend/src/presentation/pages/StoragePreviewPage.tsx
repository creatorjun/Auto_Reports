// frontend/src/presentation/pages/StoragePreviewPage.tsx
import { useNavigate, useSearchParams } from 'react-router-dom'
import FilePreviewModal from '@/presentation/components/storage/FilePreviewModal'

export default function StoragePreviewPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const name = params.get('name') ?? ''
  const folder = params.get('folder') ?? ''

  if (!name) {
    navigate('/storage', { replace: true })
    return null
  }

  return (
    <FilePreviewModal
      name={name}
      folder={folder}
      onClose={() => navigate('/storage', { replace: true })}
    />
  )
}
