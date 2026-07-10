// frontend/src/infrastructure/api/storageApi.ts
import axios from 'axios'
import type { StorageFile } from '@/domain/Storage'

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
  list: async (): Promise<StorageFile[]> => {
    const res = await storageClient.get<StorageFile[]>('/storage/')
    return res.data
  },

  upload: async (file: File): Promise<StorageFile> => {
    const form = new FormData()
    form.append('file', file)
    const res = await storageClient.post<StorageFile>('/storage/', form)
    return res.data
  },

  download: (filename: string): string => {
    return `/api/v1/storage/download/${encodeURIComponent(filename)}`
  },

  delete: async (filename: string): Promise<void> => {
    await storageClient.delete(`/storage/${encodeURIComponent(filename)}`)
  },
}
