// frontend/src/domain/Storage.ts
export interface StorageItem {
  name: string
  size: number
  uploaded_at: string
  is_dir: boolean
}

export type StorageFile = StorageItem
