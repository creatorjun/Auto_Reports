// frontend/src/presentation/components/storage/StorageCopyLinkButton.tsx
import { useEffect, useRef, useState } from 'react'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { LinkIcon } from './StorageIcons'
import { copyToClipboard } from './StorageUtils'

type CopyStatus = 'idle' | 'copied' | 'failed'

function useCopyDownloadLink(name: string, folder: string) {
  const { storage } = useApplicationServices()
  const [status, setStatus] = useState<CopyStatus>('idle')
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (resetTimer.current) clearTimeout(resetTimer.current)
  }, [])

  const handleCopy = async () => {
    if (resetTimer.current) clearTimeout(resetTimer.current)
    const downloadUrl = new URL(storage.download(name, folder), window.location.origin).toString()
    const copied = await copyToClipboard(downloadUrl)
    setStatus(copied ? 'copied' : 'failed')
    resetTimer.current = setTimeout(() => setStatus('idle'), 2000)
  }

  const label = status === 'copied' ? '다운로드 링크 복사됨' : status === 'failed' ? '링크 복사 실패' : '다운로드 링크 복사'
  const statusClass = status === 'copied'
    ? 'text-green-600 bg-green-50'
    : status === 'failed'
      ? 'text-red-500 bg-red-50'
      : 'text-apple-light hover:text-brand-600 hover:bg-brand-50'

  return { handleCopy, label, statusClass }
}

export function CopyLinkButton({ name, folder }: { name: string; folder: string }) {
  const { handleCopy, label, statusClass } = useCopyDownloadLink(name, folder)
  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${statusClass}`}
      title={label}
      aria-label={label}
    >
      <LinkIcon />
    </button>
  )
}

export function CopyLinkButtonMobile({ name, folder }: { name: string; folder: string }) {
  const { handleCopy, label, statusClass } = useCopyDownloadLink(name, folder)
  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${statusClass}`}
      title={label}
      aria-label={label}
    >
      <LinkIcon />
    </button>
  )
}
