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

export const useUploadFiles = (folder: string) => {
  const queryClient = useQueryClient()
  const [uploadingCount, setUploadingCount] = useState(0)

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
    setUploadingCount(files.length)
    await Promise.allSettled(files.map(file => storageApi.upload(file, folder, overwrite)))
    setUploadingCount(0)
    queryClient.invalidateQueries({ queryKey: ['storage', folder] })
  }, [folder, queryClient])

  return { upload, checkDuplicates, isUploading: uploadingCount > 0, uploadingCount }
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
