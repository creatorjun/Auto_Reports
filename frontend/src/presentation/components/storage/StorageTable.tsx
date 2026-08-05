// frontend/src/presentation/components/storage/StorageTable.tsx
import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { storageApi } from '@/infrastructure/api/storageApi'
import type { StorageItem } from '@/domain/Storage'
import { FolderIcon, FileIcon, EyeIcon, DownloadIcon, TrashIcon } from './StorageIcons'
import { formatBytes, isPreviewable } from './StorageUtils'
import { CopyLinkButton, CopyLinkButtonMobile } from './StorageCopyLinkButton'

export function CreateFolderRow({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  const handleSubmit = () => { const t = value.trim(); if (t) onConfirm(t) }
  return (
    <tr className="bg-brand-50/30">
      <td colSpan={4} className="px-6 py-3">
        <div className="flex items-center gap-2">
          <span className="text-brand-500"><FolderIcon /></span>
          <input ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); if (e.key === 'Escape') onCancel() }}
            placeholder="폴더 이름"
            className="flex-1 text-[13px] bg-transparent border-b border-brand-400 focus:outline-none text-apple-dark placeholder:text-apple-light/60 pb-0.5" />
          <button onClick={handleSubmit} className="text-[12px] font-medium text-brand-600 hover:text-brand-700 transition-colors px-2 py-1">만들기</button>
          <button onClick={onCancel} className="text-[12px] text-apple-light hover:text-apple-dark transition-colors px-2 py-1">취소</button>
        </div>
      </td>
    </tr>
  )
}

export function CreateFolderRowMobile({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  const handleSubmit = () => { const t = value.trim(); if (t) onConfirm(t) }
  return (
    <div className="flex items-center gap-2 px-4 py-3 bg-brand-50/30 border-b border-apple-divider/40">
      <span className="text-brand-500"><FolderIcon /></span>
      <input ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); if (e.key === 'Escape') onCancel() }}
        placeholder="폴더 이름"
        className="flex-1 text-[13px] bg-transparent border-b border-brand-400 focus:outline-none text-apple-dark placeholder:text-apple-light/60 pb-0.5" />
      <button onClick={handleSubmit} className="text-[12px] font-medium text-brand-600 px-2 py-1">만들기</button>
      <button onClick={onCancel} className="text-[12px] text-apple-light px-2 py-1">취소</button>
    </div>
  )
}

export function ItemRow({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem; folder: string
  onEnterDir: (name: string) => void; onPreview: (name: string) => void
  onDeleteFile: (name: string) => void; onDeleteDir: (name: string) => void
}) {
  const formattedDate = format(new Date(item.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  const canPreview = !item.is_dir && isPreviewable(item.name)
  return (
    <tr className="hover:bg-apple-gray/60 transition-colors duration-150">
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center gap-2">
          <span className={item.is_dir ? 'text-brand-500' : 'text-apple-light'}>
            {item.is_dir ? <FolderIcon /> : <FileIcon />}
          </span>
          {item.is_dir ? (
            <button onClick={() => onEnterDir(item.name)} className="text-[13px] 3xl:text-[14px] font-medium text-brand-600 hover:text-brand-700 hover:underline transition-colors text-left break-all">{item.name}</button>
          ) : canPreview ? (
            <button onClick={() => onPreview(item.name)} className="text-[13px] 3xl:text-[14px] text-apple-dark hover:text-brand-600 hover:underline transition-colors text-left break-all">{item.name}</button>
          ) : (
            <span className="text-[13px] 3xl:text-[14px] text-apple-dark break-all">{item.name}</span>
          )}
        </div>
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{item.is_dir ? '—' : formatBytes(item.size)}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{formattedDate}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-1.5">
          {canPreview && <button onClick={() => onPreview(item.name)} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors" title="미리보기"><EyeIcon /></button>}
          {!item.is_dir && <CopyLinkButton name={item.name} folder={folder} />}
          {!item.is_dir && <a href={storageApi.download(item.name, folder)} download={item.name} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors" title="다운로드"><DownloadIcon /></a>}
          <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors" title="삭제"><TrashIcon /></button>
        </div>
      </td>
    </tr>
  )
}

export function ItemRowMobile({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem; folder: string
  onEnterDir: (name: string) => void; onPreview: (name: string) => void
  onDeleteFile: (name: string) => void; onDeleteDir: (name: string) => void
}) {
  const formattedDate = format(new Date(item.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  const canPreview = !item.is_dir && isPreviewable(item.name)
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <div className="flex items-center gap-2 flex-1 min-w-0 pr-3">
        <span className={`flex-shrink-0 ${item.is_dir ? 'text-brand-500' : 'text-apple-light'}`}>{item.is_dir ? <FolderIcon /> : <FileIcon />}</span>
        {item.is_dir ? (
          <button onClick={() => onEnterDir(item.name)} className="flex flex-col gap-0.5 min-w-0 text-left">
            <span className="text-[13px] font-medium text-brand-600 truncate">{item.name}</span>
            <span className="text-[11px] text-apple-light">{formattedDate}</span>
          </button>
        ) : (
          <button onClick={() => canPreview ? onPreview(item.name) : undefined} className={`flex flex-col gap-0.5 min-w-0 text-left ${canPreview ? 'cursor-pointer' : 'cursor-default'}`}>
            <span className={`text-[13px] font-medium truncate ${canPreview ? 'text-apple-dark hover:text-brand-600' : 'text-apple-dark'}`}>{item.name}</span>
            <span className="text-[11px] text-apple-light">{formatBytes(item.size)} · {formattedDate}</span>
          </button>
        )}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {canPreview && <button onClick={() => onPreview(item.name)} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"><EyeIcon /></button>}
        {!item.is_dir && <CopyLinkButtonMobile name={item.name} folder={folder} />}
        {!item.is_dir && <a href={storageApi.download(item.name, folder)} download={item.name} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"><DownloadIcon /></a>}
        <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"><TrashIcon /></button>
      </div>
    </div>
  )
}
