// frontend/src/presentation/components/storage/StorageUtils.tsx
import type { BinaryContent } from '@/application/ports/ApplicationServices'
export function isPreviewable(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf', 'mp4', 'webm', 'mp3', 'wav', 'txt', 'md', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt'].includes(ext)
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

export function saveBinaryContent(content: BinaryContent, filename: string): void {
  const objectUrl = content.createObjectUrl()
  const anchor = document.createElement('a')
  anchor.href = objectUrl.url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(objectUrl.close, 1000)
}

export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
    }
  }

  const activeElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.opacity = '0'

  try {
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    return document.execCommand('copy')
  } catch {
    return false
  } finally {
    textArea.remove()
    activeElement?.focus()
  }
}
