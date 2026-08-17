// frontend/src/presentation/components/storage/StorageDrag.ts
export const STORAGE_ENTRY_DRAG_TYPE = 'application/x-auto-reports-storage-entry'

export interface DraggedStorageEntry {
  name: string
  isDir: boolean
  sourceFolder: string
}
