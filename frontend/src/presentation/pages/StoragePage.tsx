// frontend/src/presentation/pages/StoragePage.tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  useCreateFolder,
  useDeleteFolder,
  useDeleteStorageFile,
  useMoveStorageEntry,
  useStorageItems,
  useStorageQuota,
  useUploadFiles,
  QuotaExceededError,
  type DuplicateFile,
} from '@/presentation/hooks/useStorage'
import { RequestError } from '@/application/errors/RequestError'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import FilePreviewModal from '@/presentation/components/storage/FilePreviewModal'
import StorageNavigation from '@/presentation/components/storage/StorageNavigation'
import {
  QuotaBar,
  DeleteConfirmModal,
  QuotaExceededModal,
  OverwriteConfirmModal,
  UploadProgressBar,
} from '@/presentation/components/storage/StorageModals'
import {
  CreateFolderRow,
  CreateFolderRowMobile,
  ItemRow,
  ItemRowMobile,
} from '@/presentation/components/storage/StorageTable'
import {
  STORAGE_ENTRY_DRAG_TYPE,
  type DraggedStorageEntry,
} from '@/presentation/components/storage/StorageDrag'
import { isPreviewable, formatBytes, joinPath } from '@/presentation/components/storage/StorageUtils'

type ConfirmTarget = { name: string; isDir: boolean } | null
type FolderHistory = { entries: string[]; index: number }
type MoveFeedback = { type: 'success' | 'error'; message: string } | null

function getMoveErrorMessage(error: unknown): string {
  if (error instanceof RequestError && error.status === 409) {
    return '대상 폴더에 같은 이름의 파일 또는 폴더가 있습니다.'
  }
  if (error instanceof RequestError && error.status === 404) {
    return '이동할 항목이나 대상 폴더를 찾을 수 없습니다.'
  }
  if (error instanceof RequestError && error.status === 400) {
    return '해당 위치로 이동할 수 없습니다.'
  }
  return '이동 중 오류가 발생했습니다.'
}

export default function StoragePage() {
  const [folderHistory, setFolderHistory] = useState<FolderHistory>({ entries: [''], index: 0 })
  const folder = folderHistory.entries[folderHistory.index]
  const { data, isLoading, isFetching } = useStorageItems(folder)
  const { data: quota } = useStorageQuota()
  const { upload, checkDuplicates, isUploading, uploadingCount, progressList, totalPercent } = useUploadFiles(folder)
  const { mutate: createFolder, isPending: isCreating } = useCreateFolder(folder)
  const { mutate: deleteFolder, isPending: isDeletingDir } = useDeleteFolder(folder)
  const { mutate: deleteFile, isPending: isDeletingFile } = useDeleteStorageFile(folder)
  const { mutate: moveEntry, isPending: isMoving } = useMoveStorageEntry()

  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget>(null)
  const [previewTarget, setPreviewTarget] = useState<string | null>(null)
  const [isUploadDragging, setIsUploadDragging] = useState(false)
  const [draggedEntry, setDraggedEntry] = useState<DraggedStorageEntry | null>(null)
  const [moveFeedback, setMoveFeedback] = useState<MoveFeedback>(null)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<DuplicateFile[] | null>(null)
  const [quotaError, setQuotaError] = useState<{ available: number; needed: number } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const moveFeedbackTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (moveFeedbackTimer.current !== null) window.clearTimeout(moveFeedbackTimer.current)
  }, [])

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
    setIsUploadDragging(false)
    if (Array.from(e.dataTransfer.types).includes(STORAGE_ENTRY_DRAG_TYPE)) return
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (Array.from(e.dataTransfer.types).includes(STORAGE_ENTRY_DRAG_TYPE)) {
      setIsUploadDragging(false)
      return
    }
    e.preventDefault(); e.stopPropagation()
    setIsUploadDragging(true)
  }, [])

  const showMoveFeedback = useCallback((feedback: Exclude<MoveFeedback, null>) => {
    setMoveFeedback(feedback)
    if (moveFeedbackTimer.current !== null) window.clearTimeout(moveFeedbackTimer.current)
    moveFeedbackTimer.current = window.setTimeout(() => setMoveFeedback(null), 3200)
  }, [])

  const handleMove = useCallback((entry: DraggedStorageEntry, destinationFolder: string) => {
    if (isMoving || destinationFolder === entry.sourceFolder) return
    const sourcePath = joinPath(entry.sourceFolder, entry.name)
    if (entry.isDir && (destinationFolder === sourcePath || destinationFolder.startsWith(`${sourcePath}/`))) {
      showMoveFeedback({ type: 'error', message: '폴더를 자기 자신 또는 하위 폴더로 이동할 수 없습니다.' })
      setDraggedEntry(null)
      return
    }
    moveEntry(
      {
        name: entry.name,
        sourceFolder: entry.sourceFolder,
        destinationFolder,
      },
      {
        onSuccess: () => {
          const destinationLabel = destinationFolder.split('/').pop() || '보관함'
          showMoveFeedback({ type: 'success', message: `${entry.name} → ${destinationLabel} 이동 완료` })
        },
        onError: (error) => {
          showMoveFeedback({ type: 'error', message: getMoveErrorMessage(error) })
        },
        onSettled: () => setDraggedEntry(null),
      },
    )
  }, [isMoving, moveEntry, showMoveFeedback])

  const handleMoveToFolder = useCallback((destinationFolder: string) => {
    if (draggedEntry) handleMove(draggedEntry, destinationFolder)
  }, [draggedEntry, handleMove])

  const navigateToFolder = (target: string) => {
    setFolderHistory((current) => {
      if (current.entries[current.index] === target) return current
      return {
        entries: [...current.entries.slice(0, current.index + 1), target],
        index: current.index + 1,
      }
    })
    setShowNewFolder(false)
  }

  const handleEnterDir = (name: string) => {
    navigateToFolder(joinPath(folder, name))
  }

  const navigateTo = (index: number) => {
    const breadcrumbs = folder ? folder.split('/') : []
    navigateToFolder(index < 0 ? '' : breadcrumbs.slice(0, index + 1).join('/'))
  }

  const navigateBack = () => {
    setFolderHistory((current) => ({ ...current, index: Math.max(0, current.index - 1) }))
    setShowNewFolder(false)
  }

  const navigateForward = () => {
    setFolderHistory((current) => ({
      ...current,
      index: Math.min(current.entries.length - 1, current.index + 1),
    }))
    setShowNewFolder(false)
  }

  const navigateUp = () => {
    const parent = folder.split('/').slice(0, -1).join('/')
    navigateToFolder(parent)
  }

  const canGoBack = folderHistory.index > 0
  const canGoForward = folderHistory.index < folderHistory.entries.length - 1

  const handleCreateFolder = () => {
    setShowNewFolder(true)
  }

  const handleCancelCreateFolder = () => {
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

      <StorageNavigation
        folder={folder}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        onBack={navigateBack}
        onForward={navigateForward}
        onUp={navigateUp}
        onNavigateTo={navigateTo}
        onCreateFolder={handleCreateFolder}
        isCreateDisabled={showNewFolder || isCreating}
        dragSourceFolder={draggedEntry?.sourceFolder ?? null}
        isMoving={isMoving}
        onMoveToFolder={handleMoveToFolder}
      />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-apple-light">
          파일 또는 폴더를 다른 폴더나 상단 경로로 드래그해 이동할 수 있습니다.
        </p>
        {isMoving && <span className="text-[11px] font-medium text-brand-600">이동 중...</span>}
      </div>

      {moveFeedback && (
        <div
          role={moveFeedback.type === 'error' ? 'alert' : 'status'}
          aria-live="polite"
          className={`rounded-xl border px-3.5 py-2.5 text-[12px] font-medium ${
            moveFeedback.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-700'
              : 'border-red-200 bg-red-50 text-red-600'
          }`}
        >
          {moveFeedback.message}
        </div>
      )}

      <div
        className={`card border-2 border-dashed transition-colors duration-200 cursor-pointer ${
          isUploadDragging ? 'border-brand-400 bg-brand-50/40' : 'border-apple-divider hover:border-brand-300'
        }`}
        onDragOver={handleDragOver} onDragEnter={handleDragOver}
        onDragLeave={(e) => { e.preventDefault(); setIsUploadDragging(false) }}
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
                  onCancel={handleCancelCreateFolder}
                />
              )}
              {(data ?? []).map((item) => (
                <ItemRow key={item.name} item={item} folder={folder}
                  draggedEntry={draggedEntry} isMoving={isMoving}
                  onDragStart={setDraggedEntry} onDragEnd={() => setDraggedEntry(null)}
                  onMove={handleMove}
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
              onCancel={handleCancelCreateFolder}
            />
          )}
          {(data ?? []).map((item) => (
            <ItemRowMobile key={item.name} item={item} folder={folder}
              draggedEntry={draggedEntry} isMoving={isMoving}
              onDragStart={setDraggedEntry} onDragEnd={() => setDraggedEntry(null)}
              onMove={handleMove}
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
