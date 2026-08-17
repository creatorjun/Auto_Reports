// frontend/src/presentation/pages/StoragePage.tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, Trash2, X } from 'lucide-react'
import {
  useCreateFolder,
  useDeleteFolder,
  useDeleteStorageSelection,
  useDeleteStorageFile,
  useDownloadStorageSelection,
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
  SelectionDeleteConfirmModal,
  QuotaExceededModal,
  OverwriteConfirmModal,
  UploadProgressBar,
} from '@/presentation/components/storage/StorageModals'
import {
  CreateFolderRow,
  CreateFolderRowMobile,
  ItemRow,
  ItemRowMobile,
  SelectionCheckbox,
} from '@/presentation/components/storage/StorageTable'
import {
  STORAGE_ENTRY_DRAG_TYPE,
  type DraggedStorageEntry,
} from '@/presentation/components/storage/StorageDrag'
import { isPreviewable, formatBytes, joinPath, saveBlob } from '@/presentation/components/storage/StorageUtils'

type ConfirmTarget = { name: string; isDir: boolean } | null
type FolderHistory = { entries: string[]; index: number }
type StorageFeedback = { type: 'success' | 'error'; message: string } | null

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

function getSelectionErrorMessage(error: unknown, action: 'download' | 'delete'): string {
  if (error instanceof RequestError && error.status === 404) {
    return '선택한 항목 중 찾을 수 없는 파일 또는 폴더가 있습니다.'
  }
  if (error instanceof RequestError && error.status === 400) {
    return '선택 항목을 처리할 수 없습니다. 목록을 새로고침한 후 다시 시도하세요.'
  }
  return action === 'download'
    ? '선택 항목 다운로드 중 오류가 발생했습니다.'
    : '선택 항목 삭제 중 오류가 발생했습니다.'
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
  const { mutate: downloadSelection, isPending: isDownloadingSelection } = useDownloadStorageSelection(folder)
  const { mutate: deleteSelection, isPending: isDeletingSelection } = useDeleteStorageSelection(folder)

  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget>(null)
  const [previewTarget, setPreviewTarget] = useState<string | null>(null)
  const [isUploadDragging, setIsUploadDragging] = useState(false)
  const [draggedEntry, setDraggedEntry] = useState<DraggedStorageEntry | null>(null)
  const [selectedNames, setSelectedNames] = useState<Set<string>>(() => new Set())
  const [showSelectionDelete, setShowSelectionDelete] = useState(false)
  const [storageFeedback, setStorageFeedback] = useState<StorageFeedback>(null)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<DuplicateFile[] | null>(null)
  const [quotaError, setQuotaError] = useState<{ available: number; needed: number } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const feedbackTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current)
  }, [])

  useEffect(() => {
    setSelectedNames(new Set())
    setShowSelectionDelete(false)
  }, [folder])

  useEffect(() => {
    if (!data) return
    const available = new Set(data.map((item) => item.name))
    setSelectedNames((current) => {
      const next = new Set([...current].filter((name) => available.has(name)))
      return next.size === current.size ? current : next
    })
  }, [data])

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

  const showFeedback = useCallback((feedback: Exclude<StorageFeedback, null>) => {
    setStorageFeedback(feedback)
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current)
    feedbackTimer.current = window.setTimeout(() => setStorageFeedback(null), 3200)
  }, [])

  const handleMove = useCallback((entry: DraggedStorageEntry, destinationFolder: string) => {
    if (isMoving || destinationFolder === entry.sourceFolder) return
    const sourcePath = joinPath(entry.sourceFolder, entry.name)
    if (entry.isDir && (destinationFolder === sourcePath || destinationFolder.startsWith(`${sourcePath}/`))) {
      showFeedback({ type: 'error', message: '폴더를 자기 자신 또는 하위 폴더로 이동할 수 없습니다.' })
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
          showFeedback({ type: 'success', message: `${entry.name} → ${destinationLabel} 이동 완료` })
        },
        onError: (error) => {
          showFeedback({ type: 'error', message: getMoveErrorMessage(error) })
        },
        onSettled: () => setDraggedEntry(null),
      },
    )
  }, [isMoving, moveEntry, showFeedback])

  const handleMoveToFolder = useCallback((destinationFolder: string) => {
    if (draggedEntry) handleMove(draggedEntry, destinationFolder)
  }, [draggedEntry, handleMove])

  const storageItems = data ?? []
  const selectedCount = selectedNames.size
  const allSelected = storageItems.length > 0 && selectedCount === storageItems.length
  const selectionIndeterminate = selectedCount > 0 && !allSelected
  const isSelectionBusy = isDownloadingSelection || isDeletingSelection || isMoving
  const isItemBusy = isSelectionBusy

  const handleSelectionChange = useCallback((name: string, selected: boolean) => {
    setSelectedNames((current) => {
      const next = new Set(current)
      if (selected) next.add(name)
      else next.delete(name)
      return next
    })
  }, [])

  const handleToggleAll = () => {
    setSelectedNames(allSelected ? new Set() : new Set(storageItems.map((item) => item.name)))
  }

  const handleDownloadSelection = () => {
    const names = [...selectedNames]
    if (!names.length) return
    downloadSelection(names, {
      onSuccess: (blob) => {
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
        saveBlob(blob, `storage-selection-${timestamp}.zip`)
        showFeedback({ type: 'success', message: `${names.length}개 항목 다운로드 준비 완료` })
      },
      onError: (error) => {
        showFeedback({ type: 'error', message: getSelectionErrorMessage(error, 'download') })
      },
    })
  }

  const handleConfirmSelectionDelete = () => {
    const names = [...selectedNames]
    if (!names.length) return
    deleteSelection(names, {
      onSuccess: () => {
        setSelectedNames(new Set())
        setShowSelectionDelete(false)
        showFeedback({ type: 'success', message: `${names.length}개 항목 삭제 완료` })
      },
      onError: (error) => {
        setShowSelectionDelete(false)
        showFeedback({ type: 'error', message: getSelectionErrorMessage(error, 'delete') })
      },
    })
  }

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
      {showSelectionDelete && selectedCount > 0 && (
        <SelectionDeleteConfirmModal
          count={selectedCount}
          onConfirm={handleConfirmSelectionDelete}
          onCancel={() => {
            if (!isDeletingSelection) setShowSelectionDelete(false)
          }}
          isPending={isDeletingSelection}
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
          <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">파일을 업로드하고 선택하여 다운로드 또는 삭제</p>
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
        <div className="flex items-center gap-2">
          {isMoving && <span className="text-[11px] font-medium text-brand-600">이동 중...</span>}
          <button
            type="button"
            onClick={handleToggleAll}
            disabled={!storageItems.length || isSelectionBusy}
            className="text-[11px] font-medium text-brand-600 transition-colors hover:text-brand-700 disabled:cursor-not-allowed disabled:text-apple-light"
          >
            {allSelected ? '전체 선택 해제' : '전체 선택'}
          </button>
        </div>
      </div>

      {selectedCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-200 bg-brand-50/70 px-3.5 py-2.5">
          <span className="mr-auto text-[12px] font-semibold text-brand-700">{selectedCount}개 선택</span>
          <button
            type="button"
            onClick={handleDownloadSelection}
            disabled={isSelectionBusy}
            className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-[11px] font-medium text-brand-700 shadow-sm transition-colors hover:bg-brand-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={13} strokeWidth={1.8} />
            {isDownloadingSelection ? '압축 중...' : 'ZIP 다운로드'}
          </button>
          <button
            type="button"
            onClick={() => setShowSelectionDelete(true)}
            disabled={isSelectionBusy}
            className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-[11px] font-medium text-red-600 shadow-sm transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 size={13} strokeWidth={1.8} />
            삭제
          </button>
          <button
            type="button"
            onClick={() => setSelectedNames(new Set())}
            disabled={isSelectionBusy}
            title="선택 해제"
            aria-label="선택 해제"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-apple-light transition-colors hover:bg-white hover:text-apple-dark disabled:cursor-not-allowed disabled:opacity-40"
          >
            <X size={14} strokeWidth={1.8} />
          </button>
        </div>
      )}

      {storageFeedback && (
        <div
          role={storageFeedback.type === 'error' ? 'alert' : 'status'}
          aria-live="polite"
          className={`rounded-xl border px-3.5 py-2.5 text-[12px] font-medium ${
            storageFeedback.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-700'
              : 'border-red-200 bg-red-50 text-red-600'
          }`}
        >
          {storageFeedback.message}
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
                <th className="px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wider text-apple-light 3xl:px-8 3xl:py-4 3xl:text-[12px]">
                  <div className="flex items-center gap-2">
                    <SelectionCheckbox
                      checked={allSelected}
                      indeterminate={selectionIndeterminate}
                      disabled={!storageItems.length || isSelectionBusy}
                      label="현재 폴더 전체 선택"
                      onChange={handleToggleAll}
                    />
                    이름
                  </div>
                </th>
                <th className="px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wider text-apple-light 3xl:px-8 3xl:py-4 3xl:text-[12px]">크기</th>
                <th className="px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wider text-apple-light 3xl:px-8 3xl:py-4 3xl:text-[12px]">수정일시</th>
                <th className="px-6 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wider text-apple-light 3xl:px-8 3xl:py-4 3xl:text-[12px]" />
              </tr>
            </thead>
            <tbody className="divide-y divide-apple-divider/40">
              {showNewFolder && (
                <CreateFolderRow
                  onConfirm={(name) => createFolder(name, { onSuccess: () => setShowNewFolder(false) })}
                  onCancel={handleCancelCreateFolder}
                />
              )}
              {storageItems.map((item) => (
                <ItemRow key={item.name} item={item} folder={folder}
                  selected={selectedNames.has(item.name)}
                  draggedEntry={draggedEntry} isMoving={isItemBusy}
                  onSelectionChange={handleSelectionChange}
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
          {storageItems.map((item) => (
            <ItemRowMobile key={item.name} item={item} folder={folder}
              selected={selectedNames.has(item.name)}
              draggedEntry={draggedEntry} isMoving={isItemBusy}
              onSelectionChange={handleSelectionChange}
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
