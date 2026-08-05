// frontend/src/presentation/components/storage/StorageUtils.tsx
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
