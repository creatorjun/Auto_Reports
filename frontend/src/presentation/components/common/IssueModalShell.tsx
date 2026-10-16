// frontend/src/presentation/components/common/IssueModalShell.tsx
import { useEffect, type ReactNode } from 'react'
import { MODAL_CLS, type ModalSize } from '@/presentation/config/ui'

interface Props {
  title: string
  subtitle: string
  size?: ModalSize
  onClose: () => void
  children: ReactNode
}

export default function IssueModalShell({ title, subtitle, size = 'md', onClose, children }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={MODAL_CLS.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`${MODAL_CLS.containerBase} ${MODAL_CLS.containerSize[size]} min-w-0`}>
        <div className={`${MODAL_CLS.header} gap-4`}>
          <div className="min-w-0 flex-1 break-words">
            <h2 className={MODAL_CLS.title}>{title}</h2>
            <p className={MODAL_CLS.subtitle}>{subtitle}</p>
          </div>
          <button onClick={onClose} className={`${MODAL_CLS.closeBtn} shrink-0`} aria-label="닫기">✕</button>
        </div>

        <div className={`${MODAL_CLS.body} min-h-0`}>
          {children}
        </div>

        <div className={MODAL_CLS.footer}>
          <button onClick={onClose} className={MODAL_CLS.closeText}>닫기</button>
        </div>
      </div>
    </div>
  )
}
