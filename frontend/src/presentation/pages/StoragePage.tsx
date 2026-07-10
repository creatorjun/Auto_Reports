// frontend/src/presentation/pages/StoragePage.tsx
import { useCallback, useRef, useState } from 'react'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { storageApi } from '@/infrastructure/api/storageApi'
import { useDeleteStorageFile, useStorageFiles, useUploadFile } from '@/infrastructure/hooks/useStorage'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import type { StorageFile } from '@/domain/Storage'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
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

function DeleteConfirmModal({ filename, onConfirm, onCancel, isPending }: {
  filename: string
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
            <p className="text-[14px] font-semibold text-apple-dark">파일 삭제</p>
            <p className="text-[12px] text-apple-light mt-0.5 break-all max-w-[260px]">{filename}</p>
          </div>
        </div>
        <p className="text-[13px] text-apple-dark/80 mb-5 leading-relaxed">
          이 파일을 삭제하면 복구할 수 없습니다.<br />정말 삭제하시겠습니까?
        </p>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5"
          >
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

function FileRow({ file, onDelete }: { file: StorageFile; onDelete: (name: string) => void }) {
  const formattedDate = format(new Date(file.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  return (
    <tr className="hover:bg-apple-gray/60 transition-colors duration-150">
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-dark break-all max-w-xs">{file.name}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{formatBytes(file.size)}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{formattedDate}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-2">
          <a
            href={storageApi.download(file.name)}
            download={file.name}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
            title="다운로드"
          >
            <DownloadIcon />
          </a>
          <button
            onClick={() => onDelete(file.name)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
            title="삭제"
          >
            <TrashIcon />
          </button>
        </div>
      </td>
    </tr>
  )
}

function MobileFileRow({ file, onDelete }: { file: StorageFile; onDelete: (name: string) => void }) {
  const formattedDate = format(new Date(file.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <div className="flex flex-col gap-1 flex-1 min-w-0 pr-3">
        <span className="text-[13px] font-medium text-apple-dark truncate">{file.name}</span>
        <span className="text-[11px] text-apple-light">{formatBytes(file.size)} · {formattedDate}</span>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        <a
          href={storageApi.download(file.name)}
          download={file.name}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"
        >
          <DownloadIcon />
        </a>
        <button
          onClick={() => onDelete(file.name)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  )
}

export default function StoragePage() {
  const { data, isLoading, isFetching } = useStorageFiles()
  const { mutate: uploadFile, isPending: isUploading } = useUploadFile()
  const { mutate: deleteFile, isPending: isDeleting } = useDeleteStorageFile()
  const [confirmName, setConfirmName] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return
    Array.from(files).forEach(file => uploadFile(file))
  }, [uploadFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDelete = () => {
    if (!confirmName) return
    deleteFile(confirmName, { onSuccess: () => setConfirmName(null) })
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4 md:space-y-5 3xl:space-y-7">
      {confirmName && (
        <DeleteConfirmModal
          filename={confirmName}
          onConfirm={handleDelete}
          onCancel={() => setConfirmName(null)}
          isPending={isDeleting}
        />
      )}

      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[18px] md:text-[22px] 3xl:text-[26px] font-semibold text-apple-dark tracking-tight">파일 보관함</h1>
          <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">파일을 업로드하고 언제든지 다운로드</p>
        </div>
        {isFetching && !isLoading && (
          <span className="text-[11px] text-apple-light">업데이트 중...</span>
        )}
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
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
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
                {['파일명', '크기', '업로드 일시', ''].map((h, i) => (
                  <th key={i} className="text-left px-6 py-3.5 3xl:px-8 3xl:py-4 text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-divider/40">
              {(data ?? []).map((f) => (
                <FileRow key={f.name} file={f} onDelete={setConfirmName} />
              ))}
            </tbody>
          </table>
        </div>

        <div className="md:hidden divide-y divide-apple-divider/40">
          {(data ?? []).map((f) => (
            <MobileFileRow key={f.name} file={f} onDelete={setConfirmName} />
          ))}
        </div>

        {!data?.length && (
          <p className="text-center text-[13px] text-apple-light py-16">업로드된 파일이 없습니다.</p>
        )}
      </div>
    </div>
  )
}
