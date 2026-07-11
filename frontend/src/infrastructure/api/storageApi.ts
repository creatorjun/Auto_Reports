// frontend/src/infrastructure/api/storageApi.ts
import client from './client'
import type { StorageItem } from '@/domain/Storage'

export interface StorageQuota {
  used: number
  limit: number
  available: number
  percent: number
}

export interface ChunkInitResponse {
  upload_id: string
}

const CHUNK_SIZE = 8 * 1024 * 1024  // 8MB per chunk

export const storageApi = {
  list: async (folder = ''): Promise<StorageItem[]> => {
    const res = await client.get<StorageItem[]>('/storage/items', { params: { folder } })
    return res.data
  },

  checkExists: async (name: string, folder = ''): Promise<boolean> => {
    const res = await client.get<{ exists: boolean }>('/storage/check', { params: { name, folder } })
    return res.data.exists
  },

  getQuota: async (): Promise<StorageQuota> => {
    const res = await client.get<StorageQuota>('/storage/quota')
    return res.data
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
    if (file.size > CHUNK_SIZE) {
      return storageApi.uploadChunked(file, folder, overwrite, onProgress)
    }
    const form = new FormData()
    form.append('file', file)
    const res = await client.post<StorageItem>('/storage/upload', form, {
      params: { folder, overwrite, file_size: file.size },
      headers: { 'Content-Type': undefined },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
    return res.data
  },

  uploadChunked: async (
    file: File,
    folder = '',
    overwrite = false,
    onProgress?: (percent: number) => void,
  ): Promise<StorageItem> => {
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

    const initRes = await client.post<ChunkInitResponse>('/storage/upload/init', {
      folder,
      filename: file.name,
      total_size: file.size,
      overwrite,
    })
    const { upload_id } = initRes.data

    try {
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size)
        const chunk = file.slice(start, end)
        const form = new FormData()
        form.append('file', new File([chunk], file.name))
        await client.post('/storage/upload/chunk', form, {
          params: { upload_id, chunk_index: i },
          headers: { 'Content-Type': undefined },
        })
        if (onProgress) {
          onProgress(Math.round(((i + 1) / totalChunks) * 95))
        }
      }

      const res = await client.post<StorageItem>('/storage/upload/complete', {
        upload_id,
        total_chunks: totalChunks,
      })
      if (onProgress) onProgress(100)
      return res.data
    } catch (err) {
      await client.delete('/storage/upload/abort', { params: { upload_id } }).catch(() => {})
      throw err
    }
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
