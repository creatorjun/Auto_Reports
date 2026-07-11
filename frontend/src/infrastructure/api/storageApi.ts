// frontend/src/infrastructure/api/storageApi.ts
import client from './client'
import type { StorageItem } from '@/domain/Storage'

export const storageApi = {
  list: async (folder = ''): Promise<StorageItem[]> => {
    const res = await client.get<StorageItem[]>('/storage/items', { params: { folder } })
    return res.data
  },

  checkExists: async (name: string, folder = ''): Promise<boolean> => {
    const res = await client.get<{ exists: boolean }>('/storage/check', { params: { name, folder } })
    return res.data.exists
  },

  createFolder: async (name: string, folder = ''): Promise<void> => {
    await client.post('/storage/folders', { name, folder })
  },

  deleteFolder: async (name: string, folder = ''): Promise<void> => {
    await client.delete('/storage/folders', { params: { name, folder } })
  },

  upload: async (
    file: File,
    folder = '',
    overwrite = false,
    onProgress?: (percent: number) => void,
  ): Promise<StorageItem> => {
    const form = new FormData()
    form.append('file', file)
    const res = await client.post<StorageItem>('/storage/upload', form, {
      params: { folder, overwrite },
      headers: { 'Content-Type': undefined },
      timeout: 0,
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
    return res.data
  },

  preview: (name: string, folder = ''): string => {
    const token = localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage') ?? '{}')?.state?.accessToken
      : null
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    if (token) p.set('_t', token)
    return `/api/v1/storage/preview?${p.toString()}`
  },

  download: (name: string, folder = ''): string => {
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    return `/api/v1/storage/download?${p.toString()}`
  },

  deleteFile: async (name: string, folder = ''): Promise<void> => {
    await client.delete('/storage/files', { params: { name, folder } })
  },
}
