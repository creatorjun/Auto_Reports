// frontend/src/presentation/components/storage/LazyFilePreviewModal.tsx
import { useEffect, useState, type ComponentProps } from 'react'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

type PreviewComponent = typeof import('./FilePreviewModal')['default']
type Props = ComponentProps<PreviewComponent>

let loadedPreview: PreviewComponent | null = null

export default function LazyFilePreviewModal(props: Props) {
  const [Preview, setPreview] = useState<PreviewComponent | null>(() => loadedPreview)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (Preview) return
    let active = true
    import('./FilePreviewModal').then((module) => {
      loadedPreview = module.default
      if (active) setPreview(() => module.default)
    }).catch(() => {
      if (active) setFailed(true)
    })
    return () => { active = false }
  }, [Preview])

  if (Preview) return <Preview {...props} />

  return (
    <IssueModalShell title={props.name} subtitle="파일 미리보기" onClose={props.onClose}>
      {failed ? (
        <p role="alert" className="py-10 text-center text-label text-red-500">
          미리보기를 불러오지 못했습니다. 닫은 후 다시 시도해 주세요.
        </p>
      ) : <LoadingSpinner text="미리보기 불러오는 중..." />}
    </IssueModalShell>
  )
}
