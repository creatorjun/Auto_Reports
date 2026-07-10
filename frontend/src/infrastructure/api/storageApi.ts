// frontend/src/infrastructure/api/storageApi.ts
import axios from 'axios'
import type { StorageItem } from '@/domain/Storage'

const storageClient = axios.create({
  baseURL: '/api/v1',
})

storageClient.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('Storage API Error:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)

export const storageApi = {
  list: async (folder = ''): Promise<StorageItem[]> => {
    const res = await storageClient.get<StorageItem[]>('/storage/', { params: { folder } })
    return res.data
  },

  createFolder: async (name: string, folder = ''): Promise<void> => {
    await storageClient.post('/storage/folders', { name, folder })
  },

  deleteFolder: async (name: string, folder = ''): Promise<void> => {
    await storageClient.delete('/storage/folders', { params: { name, folder } })
  },

  upload: async (file: File, folder = ''): Promise<StorageItem> => {
    const form = new FormData()
    form.append('file', file)
    const res = await storageClient.post<StorageItem>('/storage/', form, { params: { folder } })
    return res.data
  },

  download: (name: string, folder = ''): string => {
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    return `/api/v1/storage/download?${p.toString()}`
  },

  deleteFile: async (name: string, folder = ''): Promise<void> => {
    await storageClient.delete('/storage/file', { params: { name, folder } })
  },
}
