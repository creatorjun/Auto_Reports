// frontend/src/presentation/hooks/useStorage.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import type { StorageItem, StorageQuota } from '@/domain/Storage'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export const useStorageItems = (folder: string) => {
  const { storage } = useApplicationServices()
  return useQuery<StorageItem[]>({
    queryKey: ['storage', folder],
    queryFn: () => storage.list(folder),
    staleTime: 0,
    refetchOnMount: true,
  })
}

export const useStorageQuota = () => {
  const { storage } = useApplicationServices()
  return useQuery<StorageQuota>({
    queryKey: ['storage-quota'],
    queryFn: storage.getQuota,
    staleTime: 10_000,
    refetchOnMount: true,
  })
}

export const useCreateFolder = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storage.createFolder(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export const useDeleteFolder = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storage.deleteFolder(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export interface MoveStorageEntryInput {
  name: string
  sourceFolder: string
  destinationFolder: string
}

export const useMoveStorageEntry = () => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ name, sourceFolder, destinationFolder }: MoveStorageEntryInput) =>
      storage.move(name, sourceFolder, destinationFolder),
    onSuccess: (_, { sourceFolder, destinationFolder }) => {
      queryClient.invalidateQueries({ queryKey: ['storage', sourceFolder] })
      queryClient.invalidateQueries({ queryKey: ['storage', destinationFolder] })
    },
  })
}

export const useUploadFile = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, overwrite }: { file: File; overwrite: boolean }) =>
      storage.upload(file, folder, overwrite),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export interface DuplicateFile {
  file: File
  exists: boolean
}

export interface FileProgress {
  name: string
  percent: number
  done: boolean
}

export class QuotaExceededError extends Error {
  available: number
  needed: number
  constructor(available: number, needed: number) {
    super('QUOTA_EXCEEDED')
    this.available = available
    this.needed = needed
  }
}

export const useUploadFiles = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  const [progressList, setProgressList] = useState<FileProgress[]>([])

  const checkDuplicates = useCallback(async (files: File[]): Promise<DuplicateFile[]> => {
    const results = await Promise.all(
      files.map(async (file) => ({
        file,
        exists: await storage.checkExists(file.name, folder),
      }))
    )
    return results
  }, [folder, storage])

  const upload = useCallback(async (files: File[], overwrite = false) => {
    if (!files.length) return

    const quota = await storage.getQuota()
    const totalNeeded = files.reduce((sum, f) => sum + f.size, 0)
    if (totalNeeded > quota.available) {
      throw new QuotaExceededError(quota.available, totalNeeded)
    }

    setProgressList(files.map(f => ({ name: f.name, percent: 0, done: false })))
    await Promise.allSettled(
      files.map((file, idx) =>
        storage.upload(file, folder, overwrite, (percent) => {
          setProgressList(prev =>
            prev.map((p, i) => i === idx ? { ...p, percent } : p)
          )
        }).then(() => {
          setProgressList(prev =>
            prev.map((p, i) => i === idx ? { ...p, percent: 100, done: true } : p)
          )
        })
      )
    )
    queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    queryClient.invalidateQueries({ queryKey: ['storage-quota'] })
    setTimeout(() => setProgressList([]), 1200)
  }, [folder, queryClient, storage])

  const isUploading = progressList.length > 0 && progressList.some(p => !p.done)
  const uploadingCount = progressList.filter(p => !p.done).length
  const totalPercent = progressList.length > 0
    ? Math.round(progressList.reduce((sum, p) => sum + p.percent, 0) / progressList.length)
    : 0

  return { upload, checkDuplicates, isUploading, uploadingCount, progressList, totalPercent }
}

export const useDeleteStorageFile = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storage.deleteFile(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
      queryClient.invalidateQueries({ queryKey: ['storage-quota'] })
    },
  })
}
