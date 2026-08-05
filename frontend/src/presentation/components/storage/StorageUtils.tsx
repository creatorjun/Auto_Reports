// frontend/src/presentation/components/storage/StorageUtils.tsx
import { useState } from 'react'
import { LinkIcon } from './StorageIcons'

export function isPreviewable(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf', 'mp4', 'webm', 'mp3', 'wav', 'txt', 'md'].includes(ext)
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function joinPath(...parts: string[]): string {
  return parts.filter(Boolean).join('/').replace(/\/+/g, '/')
}

export function getShareUrl(name: string, folder: string): string {
  const base = window.location.origin
  const path = folder ? `${folder}/${name}` : name
  return `${base}/api/storage/share/${encodeURIComponent(path)}`
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

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
