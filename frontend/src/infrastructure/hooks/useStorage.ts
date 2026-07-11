// frontend/src/infrastructure/hooks/useStorage.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { storageApi } from '@/infrastructure/api/storageApi'
import type { StorageItem } from '@/domain/Storage'

export const useStorageItems = (folder: string) =>
  useQuery<StorageItem[]>({
    queryKey: ['storage', folder],
    queryFn: () => storageApi.list(folder),
    staleTime: 0,
    refetchOnMount: true,
  })

export const useCreateFolder = (folder: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storageApi.createFolder(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export const useDeleteFolder = (folder: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storageApi.deleteFolder(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export const useUploadFile = (folder: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, overwrite }: { file: File; overwrite: boolean }) =>
      storageApi.upload(file, folder, overwrite),
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

export const useUploadFiles = (folder: string) => {
  const queryClient = useQueryClient()
  const [progressList, setProgressList] = useState<FileProgress[]>([])

  const checkDuplicates = useCallback(async (files: File[]): Promise<DuplicateFile[]> => {
    const results = await Promise.all(
      files.map(async (file) => ({
        file,
        exists: await storageApi.checkExists(file.name, folder),
      }))
    )
    return results
  }, [folder])

  const upload = useCallback(async (files: File[], overwrite = false) => {
    if (!files.length) return
    setProgressList(files.map(f => ({ name: f.name, percent: 0, done: false })))
    await Promise.allSettled(
      files.map((file, idx) =>
        storageApi.upload(file, folder, overwrite, (percent) => {
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
    setTimeout(() => setProgressList([]), 1200)
  }, [folder, queryClient])

  const isUploading = progressList.length > 0 && progressList.some(p => !p.done)
  const uploadingCount = progressList.filter(p => !p.done).length
  const totalPercent = progressList.length > 0
    ? Math.round(progressList.reduce((sum, p) => sum + p.percent, 0) / progressList.length)
    : 0

  return { upload, checkDuplicates, isUploading, uploadingCount, progressList, totalPercent }
}

export const useDeleteStorageFile = (folder: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => storageApi.deleteFile(name, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}
