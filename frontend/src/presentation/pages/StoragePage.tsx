// frontend/src/presentation/pages/StoragePage.tsx
import { useCallback, useRef, useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { storageApi } from '@/infrastructure/api/storageApi'
import {
  useCreateFolder,
  useDeleteFolder,
  useDeleteStorageFile,
  useStorageItems,
  useUploadFile,
} from '@/infrastructure/hooks/useStorage'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import FilePreviewModal from '@/presentation/components/storage/FilePreviewModal'
import type { StorageItem } from '@/domain/Storage'

const PREVIEWABLE_EXTS = new Set([
  'png','jpg','jpeg','gif','webp','svg','bmp','ico',
  'mp4','webm','ogg','mov',
  'pdf',
  'txt','log','sh','py','ts','tsx','js','jsx','css','html','env',
  'md','csv','json','yaml','yml','xml','toml',
  'xlsx','xls','docx','doc','pptx','ppt',
])

function isPreviewable(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return PREVIEWABLE_EXTS.has(ext)
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function joinPath(...parts: string[]): string {
  return parts.filter(Boolean).join('/')
}

function FolderIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M1.5 4.5A1 1 0 0 1 2.5 3.5h3.086a1 1 0 0 1 .707.293L7.207 4.707A1 1 0 0 0 7.914 5H13.5a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1V4.5Z" fill="currentColor" opacity="0.2" stroke="currentColor" strokeWidth="1.1" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 1.5h5.5L11 4v8.5a.5.5 0 0 1-.5.5h-7a.5.5 0 0 1-.5-.5v-11A.5.5 0 0 1 3 1.5Z" stroke="currentColor" strokeWidth="1.1" fill="currentColor" opacity="0.1" />
      <path d="M8.5 1.5V4H11" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M1 7s2.5-4.5 6-4.5S13 7 13 7s-2.5 4.5-6 4.5S1 7 1 7Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      <circle cx="7" cy="7" r="1.8" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 3.5h10M5.5 3.5V2.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M11.5 3.5l-.6 7.2a1 1 0 0 1-1 .8H4.1a1 1 0 0 1-1-.8L2.5 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 6.5v3M8.5 6.5v3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 2v7M4 6.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M2 10.5v1a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5v-1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function DeleteConfirmModal({ target, isDir, onConfirm, onCancel, isPending }: {
  target: string
  isDir: boolean
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-[320px] md:w-[380px] mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3.75v5.5M9 11.75v.5" stroke="#ef4444" strokeWidth="1.6" strokeLinecap="round" />
              <path d="M7.273 2.5h3.454c.28 0 .537.15.674.393l4.925 8.625A.75.75 0 0 1 15.652 12.5H2.348a.75.75 0 0 1-.674-1.082l4.925-8.625A.75.75 0 0 1 7.273 2.5Z" stroke="#ef4444" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-apple-dark">{isDir ? '폴더 삭제' : '파일 삭제'}</p>
            <p className="text-[12px] text-apple-light mt-0.5 break-all max-w-[260px]">{target}</p>
          </div>
        </div>
        <p className="text-[13px] text-apple-dark/80 mb-5 leading-relaxed">
          {isDir
            ? <>폴더 내의 모든 파일이 함께 삭제됩니다.<br />정말 삭제하시겠습니까?</>
            : <>이 파일을 삭제하면 복구할 수 없습니다.<br />정말 삭제하시겠습니까?</>
          }
        </p>
        <div className="flex gap-2">
          <button onClick={onCancel} disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-50">
            취소
          </button>
          <button onClick={onConfirm} disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5">
            {isPending && (
              <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
              </svg>
            )}
            삭제
          </button>
        </div>
      </div>
    </div>
  )
}

function CreateFolderRow({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  const handleSubmit = () => { const t = value.trim(); if (t) onConfirm(t) }
  return (
    <tr className="bg-brand-50/30">
      <td className="px-6 py-3 3xl:px-8" colSpan={4}>
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

function CreateFolderRowMobile({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
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

function ItemRow({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem
  folder: string
  onEnterDir: (name: string) => void
  onPreview: (name: string) => void
  onDeleteFile: (name: string) => void
  onDeleteDir: (name: string) => void
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
            <button onClick={() => onEnterDir(item.name)}
              className="text-[13px] 3xl:text-[14px] font-medium text-brand-600 hover:text-brand-700 hover:underline transition-colors text-left break-all">
              {item.name}
            </button>
          ) : canPreview ? (
            <button onClick={() => onPreview(item.name)}
              className="text-[13px] 3xl:text-[14px] text-apple-dark hover:text-brand-600 hover:underline transition-colors text-left break-all">
              {item.name}
            </button>
          ) : (
            <span className="text-[13px] 3xl:text-[14px] text-apple-dark break-all">{item.name}</span>
          )}
        </div>
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">
        {item.is_dir ? '—' : formatBytes(item.size)}
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">
        {formattedDate}
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-2">
          {canPreview && (
            <button onClick={() => onPreview(item.name)}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
              title="미리보기">
              <EyeIcon />
            </button>
          )}
          {!item.is_dir && (
            <a href={storageApi.download(item.name, folder)} download={item.name}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
              title="다운로드">
              <DownloadIcon />
            </a>
          )}
          <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
            title="삭제">
            <TrashIcon />
          </button>
        </div>
      </td>
    </tr>
  )
}

function ItemRowMobile({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem
  folder: string
  onEnterDir: (name: string) => void
  onPreview: (name: string) => void
  onDeleteFile: (name: string) => void
  onDeleteDir: (name: string) => void
}) {
  const formattedDate = format(new Date(item.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  const canPreview = !item.is_dir && isPreviewable(item.name)
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <div className="flex items-center gap-2 flex-1 min-w-0 pr-3">
        <span className={`flex-shrink-0 ${item.is_dir ? 'text-brand-500' : 'text-apple-light'}`}>
          {item.is_dir ? <FolderIcon /> : <FileIcon />}
        </span>
        {item.is_dir ? (
          <button onClick={() => onEnterDir(item.name)} className="flex flex-col gap-0.5 min-w-0 text-left">
            <span className="text-[13px] font-medium text-brand-600 truncate">{item.name}</span>
            <span className="text-[11px] text-apple-light">{formattedDate}</span>
          </button>
        ) : (
          <button onClick={() => canPreview ? onPreview(item.name) : undefined}
            className={`flex flex-col gap-0.5 min-w-0 text-left ${canPreview ? 'cursor-pointer' : 'cursor-default'}`}>
            <span className={`text-[13px] font-medium truncate ${canPreview ? 'text-apple-dark hover:text-brand-600' : 'text-apple-dark'}`}>{item.name}</span>
            <span className="text-[11px] text-apple-light">{formatBytes(item.size)} · {formattedDate}</span>
          </button>
        )}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {canPreview && (
          <button onClick={() => onPreview(item.name)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors">
            <EyeIcon />
          </button>
        )}
        {!item.is_dir && (
          <a href={storageApi.download(item.name, folder)} download={item.name}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors">
            <DownloadIcon />
          </a>
        )}
        <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors">
          <TrashIcon />
        </button>
      </div>
    </div>
  )
}

type ConfirmTarget = { name: string; isDir: boolean } | null

export default function StoragePage() {
  const [folder, setFolder] = useState('')
  const { data, isLoading, isFetching } = useStorageItems(folder)
  const { mutate: uploadFile, isPending: isUploading } = useUploadFile(folder)
  const { mutate: createFolder, isPending: isCreating } = useCreateFolder(folder)
  const { mutate: deleteFolder, isPending: isDeletingDir } = useDeleteFolder(folder)
  const { mutate: deleteFile, isPending: isDeletingFile } = useDeleteStorageFile(folder)

  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget>(null)
  const [previewTarget, setPreviewTarget] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const breadcrumbs = folder ? folder.split('/') : []

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return
    Array.from(files).forEach(file => uploadFile(file))
  }, [uploadFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleEnterDir = (name: string) => {
    setFolder(joinPath(folder, name))
    setShowNewFolder(false)
  }

  const navigateTo = (index: number) => {
    setFolder(index < 0 ? '' : breadcrumbs.slice(0, index + 1).join('/'))
    setShowNewFolder(false)
  }

  const handleConfirmDelete = () => {
    if (!confirmTarget) return
    if (confirmTarget.isDir) {
      deleteFolder(confirmTarget.name, { onSuccess: () => setConfirmTarget(null) })
    } else {
      deleteFile(confirmTarget.name, { onSuccess: () => setConfirmTarget(null) })
    }
  }

  const isDeleting = isDeletingDir || isDeletingFile

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4 md:space-y-5 3xl:space-y-7">
      {confirmTarget && (
        <DeleteConfirmModal
          target={confirmTarget.name}
          isDir={confirmTarget.isDir}
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmTarget(null)}
          isPending={isDeleting}
        />
      )}
      {previewTarget && (
        <FilePreviewModal
          name={previewTarget}
          folder={folder}
          onClose={() => setPreviewTarget(null)}
        />
      )}

      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[18px] md:text-[22px] 3xl:text-[26px] font-semibold text-apple-dark tracking-tight">파일 보관함</h1>
          <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">파일을 업로드하고 언제든지 다운로드</p>
        </div>
        {isFetching && !isLoading && <span className="text-[11px] text-apple-light">업데이트 중...</span>}
      </div>

      <div className="flex items-center gap-1 flex-wrap">
        <button onClick={() => navigateTo(-1)}
          className={`text-[13px] transition-colors ${
            folder ? 'text-brand-600 hover:text-brand-700' : 'text-apple-dark font-medium cursor-default'
          }`}>
          보관함
        </button>
        {breadcrumbs.map((seg, i) => (
          <div key={i} className="flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-apple-divider">
              <path d="M4.5 2.5l3 3.5-3 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <button onClick={() => navigateTo(i)}
              className={`text-[13px] transition-colors ${
                i === breadcrumbs.length - 1
                  ? 'text-apple-dark font-medium cursor-default'
                  : 'text-brand-600 hover:text-brand-700'
              }`}>
              {seg}
            </button>
          </div>
        ))}
        <div className="ml-auto">
          <button onClick={() => setShowNewFolder(true)} disabled={showNewFolder || isCreating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium
                       bg-apple-gray hover:bg-apple-divider/40 text-apple-dark
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M0.75 3.75A.75.75 0 0 1 1.5 3h3.086a.75.75 0 0 1 .53.22l.664.664a.75.75 0 0 0 .53.22H11.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-.75.75h-10a.75.75 0 0 1-.75-.75V3.75Z" stroke="currentColor" strokeWidth="1.1" fill="currentColor" opacity="0.15" />
              <path d="M6.5 5.5v3M5 7h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            새 폴더
          </button>
        </div>
      </div>

      <div
        className={`card border-2 border-dashed transition-colors duration-200 cursor-pointer ${
          isDragging ? 'border-brand-400 bg-brand-50/40' : 'border-apple-divider hover:border-brand-300'
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          {isUploading ? (
            <svg className="animate-spin w-7 h-7 text-brand-500" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-apple-light">
              <path d="M12 16V8M8 12l4-4 4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M3 16.5V19a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-2.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          )}
          <div className="text-center">
            <p className="text-[13px] font-medium text-apple-dark">
              {isUploading ? '업로드 중...' : '클릭하거나 파일을 드래그하세요'}
            </p>
            <p className="text-[11px] text-apple-light mt-0.5">크기 및 확장자 제한 없음</p>
          </div>
        </div>
      </div>

      <div className={`card overflow-hidden p-0 transition-opacity duration-200 ${isFetching ? 'opacity-70' : 'opacity-100'}`}>
        <div className="hidden md:block">
          <table className="w-full">
            <thead className="border-b border-apple-divider/60">
              <tr>
                {['이름', '크기', '수정일시', ''].map((h, i) => (
                  <th key={i} className="text-left px-6 py-3.5 3xl:px-8 3xl:py-4 text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-divider/40">
              {showNewFolder && (
                <CreateFolderRow
                  onConfirm={(name) => createFolder(name, { onSuccess: () => setShowNewFolder(false) })}
                  onCancel={() => setShowNewFolder(false)}
                />
              )}
              {(data ?? []).map((item) => (
                <ItemRow
                  key={item.name}
                  item={item}
                  folder={folder}
                  onEnterDir={handleEnterDir}
                  onPreview={setPreviewTarget}
                  onDeleteFile={(name) => setConfirmTarget({ name, isDir: false })}
                  onDeleteDir={(name) => setConfirmTarget({ name, isDir: true })}
                />
              ))}
            </tbody>
          </table>
        </div>
        <div className="md:hidden divide-y divide-apple-divider/40">
          {showNewFolder && (
            <CreateFolderRowMobile
              onConfirm={(name) => createFolder(name, { onSuccess: () => setShowNewFolder(false) })}
              onCancel={() => setShowNewFolder(false)}
            />
          )}
          {(data ?? []).map((item) => (
            <ItemRowMobile
              key={item.name}
              item={item}
              folder={folder}
              onEnterDir={handleEnterDir}
              onPreview={setPreviewTarget}
              onDeleteFile={(name) => setConfirmTarget({ name, isDir: false })}
              onDeleteDir={(name) => setConfirmTarget({ name, isDir: true })}
            />
          ))}
        </div>
        {!data?.length && !showNewFolder && (
          <p className="text-center text-[13px] text-apple-light py-16">이 폴더는 비어 있습니다.</p>
        )}
      </div>
    </div>
  )
}
