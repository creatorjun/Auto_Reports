// frontend/src/presentation/components/storage/StorageUtils.tsx
import { useState } from 'react'
import { LinkIcon } from './StorageIcons'

const PREVIEWABLE_EXTS = new Set([
  'png','jpg','jpeg','gif','webp','svg','bmp','ico',
  'mp4','webm','ogg','mov',
  'pdf',
  'txt','log','sh','py','ts','tsx','js','jsx','css','html','env',
  'md','csv','json','yaml','yml','xml','toml',
  'xlsx','xls','docx','doc','pptx','ppt',
])

export function isPreviewable(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return PREVIEWABLE_EXTS.has(ext)
}

export function getShareUrl(name: string, folder: string): string {
  const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
  return `${window.location.origin}/storage/preview?${p.toString()}`
}

export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0;'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!ok) throw new Error('execCommand copy failed')
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export function joinPath(...parts: string[]): string {
  return parts.filter(Boolean).join('/')
}

export function CopyLinkButton({ name, folder }: { name: string; folder: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await copyToClipboard(getShareUrl(name, folder))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      alert('링크 복사에 실패했습니다.\n' + getShareUrl(name, folder))
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors text-apple-light hover:text-brand-600 hover:bg-brand-50"
      title="링크 복사"
    >
      {copied
        ? <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 7l3 3 6-6" stroke="#22c55e" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
        : <LinkIcon />}
    </button>
  )
}

export function CopyLinkButtonMobile({ name, folder }: { name: string; folder: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await copyToClipboard(getShareUrl(name, folder))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      alert('링크 복사에 실패했습니다.\n' + getShareUrl(name, folder))
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors text-apple-light hover:text-brand-600 hover:bg-brand-50"
      title="링크 복사"
    >
      {copied
        ? <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 7l3 3 6-6" stroke="#22c55e" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
        : <LinkIcon />}
    </button>
  )
}
