// frontend/src/infrastructure/api/storageApi.ts
import client, { getAccessToken } from './client'
import { createBinaryContent } from './binaryContent'
import type {
  BinaryContent,
  StorageGateway,
  UploadSource,
} from '@/application/ports/ApplicationServices'
import type { StorageItem, StorageQuota } from '@/domain/Storage'

export interface ChunkInitResponse {
  upload_id: string
}

const CHUNK_SIZE = 8 * 1024 * 1024

async function uploadChunked(
  file: UploadSource,
  folder = '',
  overwrite = false,
  onProgress?: (percent: number) => void,
): Promise<StorageItem> {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  const initRes = await client.post<ChunkInitResponse>('/storage/upload/init', {
    folder,
    filename: file.name,
    total_size: file.size,
    overwrite,
  })
  const { upload_id } = initRes.data

  try {
    for (let index = 0; index < totalChunks; index++) {
      const start = index * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = await file.read(start, end)
      const form = new FormData()
      form.append('file', new File([chunk], file.name, { type: file.mediaType }))
      await client.post('/storage/upload/chunk', form, {
        params: { upload_id, chunk_index: index },
        headers: { 'Content-Type': undefined },
      })
      onProgress?.(Math.round(((index + 1) / totalChunks) * 95))
    }

    const response = await client.post<StorageItem>('/storage/upload/complete', {
      upload_id,
      total_chunks: totalChunks,
    })
    onProgress?.(100)
    return response.data
  } catch (error) {
    await client.delete('/storage/upload/abort', { params: { upload_id } }).catch(() => {})
    throw error
  }
}

export const storageApi: StorageGateway = {
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

  move: async (name: string, sourceFolder: string, destinationFolder: string): Promise<void> => {
    await client.post('/storage/move', {
      name,
      source_folder: sourceFolder,
      destination_folder: destinationFolder,
    })
  },

  downloadSelection: async (folder: string, names: string[]): Promise<BinaryContent> => {
    const res = await client.post<Blob>(
      '/storage/selection/archive',
      { folder, names },
      { responseType: 'blob' },
    )
    return createBinaryContent(res.data)
  },

  deleteSelection: async (folder: string, names: string[]): Promise<void> => {
    await client.post('/storage/selection/delete', { folder, names })
  },

  upload: async (
    file: UploadSource,
    folder = '',
    overwrite = false,
    onProgress?: (percent: number) => void,
  ): Promise<StorageItem> => {
    if (file.size > CHUNK_SIZE) {
      return uploadChunked(file, folder, overwrite, onProgress)
    }
    const form = new FormData()
    const content = await file.read(0, file.size)
    form.append('file', new File([content], file.name, { type: file.mediaType }))
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

  readPreview: async (name: string, folder = ''): Promise<BinaryContent> => {
    const response = await client.get<Blob>('/storage/preview', {
      params: { name, folder },
      responseType: 'blob',
    })
    return createBinaryContent(response.data)
  },

  convertPreview: async (name: string, folder = ''): Promise<BinaryContent> => {
    const response = await client.get<Blob>('/storage/preview-converted', {
      params: { name, folder },
      responseType: 'blob',
    })
    return createBinaryContent(response.data)
  },

  preview: (name: string, folder = ''): string => {
    const token = getAccessToken()
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    if (token) p.set('_t', token)
    return `/api/v1/storage/preview?${p.toString()}`
  },

  download: (name: string, folder = ''): string => {
    const token = getAccessToken()
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    if (token) p.set('_t', token)
    return `/api/v1/storage/download?${p.toString()}`
  },

  deleteFile: async (name: string, folder = ''): Promise<void> => {
    await client.delete('/storage/files', { params: { name, folder } })
  },
}
