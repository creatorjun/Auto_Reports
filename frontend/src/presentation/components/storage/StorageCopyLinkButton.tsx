// frontend/src/presentation/components/storage/StorageCopyLinkButton.tsx
import { useState } from 'react'
import { LinkIcon } from './StorageIcons'
import { getShareUrl, copyToClipboard } from './StorageUtils'

export function CopyLinkButton({ name, folder }: { name: string; folder: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    const url = getShareUrl(name, folder)
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
      title={copied ? '복사됨!' : '링크 복사'}
    >
      <LinkIcon />
    </button>
  )
}

export function CopyLinkButtonMobile({ name, folder }: { name: string; folder: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    const url = getShareUrl(name, folder)
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
      title={copied ? '복사됨!' : '링크 복사'}
    >
      <LinkIcon />
    </button>
  )
}
