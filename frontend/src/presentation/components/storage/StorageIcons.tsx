// frontend/src/presentation/components/storage/StorageIcons.tsx
export function FolderIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1.5 3.5C1.5 2.948 1.948 2.5 2.5 2.5H6.086a1 1 0 0 1 .707.293L7.914 3.914A1 1 0 0 0 8.621 4.2H13.5c.552 0 1 .448 1 1v7.3c0 .552-.448 1-1 1h-11c-.552 0-1-.448-1-1V3.5z" fill="currentColor" />
    </svg>
  )
}

export function FileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 1.5A1.5 1.5 0 0 0 2.5 3v10A1.5 1.5 0 0 0 4 14.5h8a1.5 1.5 0 0 0 1.5-1.5V5.621a1.5 1.5 0 0 0-.44-1.06L10.44 1.94A1.5 1.5 0 0 0 9.379 1.5H4z" fill="currentColor" opacity="0.3" />
      <path d="M9 1.5v3A1.5 1.5 0 0 0 10.5 6h3" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  )
}

export function EyeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1 7s2-4 6-4 6 4 6 4-2 4-6 4-6-4-6-4z" stroke="currentColor" strokeWidth="1.2" fill="none" />
      <circle cx="7" cy="7" r="1.5" fill="currentColor" />
    </svg>
  )
}

export function LinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M5.5 8.5a3.5 3.5 0 0 0 5 0l1.5-1.5a3.536 3.536 0 0 0-5-5L6 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M8.5 5.5a3.5 3.5 0 0 0-5 0L2 7a3.536 3.536 0 0 0 5 5L8 11" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 3.5h10M5 3.5V2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5v1M3.5 3.5l.5 8a.5.5 0 0 0 .5.5h5a.5.5 0 0 0 .5-.5l.5-8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M7 1.5v8M4 7l3 3 3-3M2.5 11h9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
