// frontend/src/presentation/pages/StoragePage.tsx
import { useCallback, useRef, useState } from 'react'
import {
  useCreateFolder,
  useDeleteFolder,
  useDeleteStorageFile,
  useStorageItems,
  useStorageQuota,
  useUploadFiles,
  QuotaExceededError,
  type DuplicateFile,
} from '@/presentation/hooks/useStorage'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import FilePreviewModal from '@/presentation/components/storage/FilePreviewModal'
import {
  QuotaBar,
  DeleteConfirmModal,
  QuotaExceededModal,
  OverwriteConfirmModal,
  UploadProgressBar,
  CreateFolderRow,
  CreateFolderRowMobile,
  ItemRow,
  ItemRowMobile,
} from '@/presentation/components/storage/StorageModals'
import { isPreviewable, formatBytes, joinPath } from '@/presentation/components/storage/StorageUtils'

type ConfirmTarget = { name: string; isDir: boolean } | null

export default function StoragePage() {
  const [folder, setFolder] = useState('')
  const { data, isLoading, isFetching } = useStorageItems(folder)
  const { data: quota } = useStorageQuota()
  const { upload, checkDuplicates, isUploading, uploadingCount, progressList, totalPercent } = useUploadFiles(folder)
  const { mutate: createFolder, isPending: isCreating } = useCreateFolder(folder)
  const { mutate: deleteFolder, isPending: isDeletingDir } = useDeleteFolder(folder)
  const { mutate: deleteFile, isPending: isDeletingFile } = useDeleteStorageFile(folder)

  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget>(null)
  const [previewTarget, setPreviewTarget] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<DuplicateFile[] | null>(null)
  const [quotaError, setQuotaError] = useState<{ available: number; needed: number } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const breadcrumbs = folder ? folder.split('/') : []

  const previewableFiles = (data ?? []).filter(item => !item.is_dir && isPreviewable(item.name)).map(item => item.name)

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const list = Array.from(files)
    const checked = await checkDuplicates(list)
    const hasDuplicates = checked.some(d => d.exists)
    if (hasDuplicates) {
      setPendingFiles(checked)
    } else {
      try {
        await upload(list, false)
      } catch (e) {
        if (e instanceof QuotaExceededError) {
          setQuotaError({ available: e.available, needed: e.needed })
        }
      }
    }
  }, [checkDuplicates, upload])

  const handleOverwriteConfirm = useCallback(async (overwriteAll: boolean) => {
    if (!pendingFiles) return
    const toUpload = overwriteAll
      ? pendingFiles.map(d => d.file)
      : pendingFiles.filter(d => !d.exists).map(d => d.file)
    setPendingFiles(null)
    try {
      await upload(toUpload, overwriteAll)
    } catch (e) {
      if (e instanceof QuotaExceededError) {
        setQuotaError({ available: e.available, needed: e.needed })
      }
    }
  }, [pendingFiles, upload])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation()
    setIsDragging(true)
  }, [])

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

  const uploadLabel = isUploading
    ? uploadingCount > 1 ? `${uploadingCount}개 업로드 중...` : '업로드 중...'
    : '클릭하거나 파일을 드래그하세요'

  return (
    <div className="space-y-4 md:space-y-5 3xl:space-y-7">
      {confirmTarget && (
        <DeleteConfirmModal
          target={confirmTarget.name} isDir={confirmTarget.isDir}
          onConfirm={handleConfirmDelete} onCancel={() => setConfirmTarget(null)}
          isPending={isDeleting}
        />
      )}
      {previewTarget && (
        <FilePreviewModal
          name={previewTarget}
          folder={folder}
          fileList={previewableFiles}
          onNavigate={setPreviewTarget}
          onClose={() => setPreviewTarget(null)}
        />
      )}
      {pendingFiles && (
        <OverwriteConfirmModal
          duplicates={pendingFiles}
          onConfirm={handleOverwriteConfirm}
          onCancel={() => setPendingFiles(null)}
        />
      )}
      {quotaError && (
        <QuotaExceededModal
          available={quotaError.available}
          needed={quotaError.needed}
          onClose={() => setQuotaError(null)}
        />
      )}

      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[18px] md:text-[22px] 3xl:text-[26px] font-semibold text-apple-dark tracking-tight">파일 보관함</h1>
          <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">파일을 업로드하고 언제든지 다운로드</p>
        </div>
        {isFetching && !isLoading && <span className="text-[11px] text-apple-light">업데이트 중...</span>}
      </div>

      {quota && (
        <QuotaBar
          used={quota.used}
          limit={quota.limit}
          available={quota.available}
          percent={quota.percent}
        />
      )}

      <div className="flex items-center gap-1 flex-wrap">
        <button onClick={() => navigateTo(-1)}
          className={`text-[13px] transition-colors ${folder ? 'text-brand-600 hover:text-brand-700' : 'text-apple-dark font-medium cursor-default'}`}>
          보관함
        </button>
        {breadcrumbs.map((seg, i) => (
          <div key={i} className="flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-apple-divider">
              <path d="M4.5 2.5l3 3.5-3 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <button onClick={() => navigateTo(i)}
              className={`text-[13px] transition-colors ${i === breadcrumbs.length - 1 ? 'text-apple-dark font-medium cursor-default' : 'text-brand-600 hover:text-brand-700'}`}>
              {seg}
            </button>
          </div>
        ))}
        <div className="ml-auto">
          <button onClick={() => setShowNewFolder(true)} disabled={showNewFolder || isCreating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
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
        onDragOver={handleDragOver} onDragEnter={handleDragOver}
        onDragLeave={(e) => { e.preventDefault(); setIsDragging(false) }}
        onDrop={handleDrop}
        onClick={() => !isUploading && inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" multiple className="hidden"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = '' }} />
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
            <p className="text-[13px] font-medium text-apple-dark">{uploadLabel}</p>
            <p className="text-[11px] text-apple-light mt-0.5">
              {quota ? `남은 용량 ${formatBytes(quota.available)}` : 'zip, tar, gz 등 모든 형식 업로드 가능'}
            </p>
          </div>
        </div>
      </div>

      <UploadProgressBar progressList={progressList} totalPercent={totalPercent} />

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
                <ItemRow key={item.name} item={item} folder={folder}
                  onEnterDir={handleEnterDir} onPreview={setPreviewTarget}
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
            <ItemRowMobile key={item.name} item={item} folder={folder}
              onEnterDir={handleEnterDir} onPreview={setPreviewTarget}
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
