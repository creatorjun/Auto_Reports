// frontend/src/infrastructure/api/storageApi.ts
import client from './client'
import type { StorageItem } from '@/domain/Storage'

export const storageApi = {
  list: async (folder = ''): Promise<StorageItem[]> => {
    const res = await client.get<StorageItem[]>('/storage/items', { params: { folder } })
    return res.data
  },

  createFolder: async (name: string, folder = ''): Promise<void> => {
    await client.post('/storage/folders', { name, folder })
  },

  deleteFolder: async (name: string, folder = ''): Promise<void> => {
    await client.delete('/storage/folders', { params: { name, folder } })
  },

  upload: async (file: File, folder = ''): Promise<StorageItem> => {
    const form = new FormData()
    form.append('file', file)
    const res = await client.post<StorageItem>('/storage/upload', form, {
      params: { folder },
      headers: { 'Content-Type': undefined },
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
