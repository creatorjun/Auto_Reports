// frontend/src/infrastructure/hooks/useStorage.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { storageApi } from '@/infrastructure/api/storageApi'
import type { StorageItem } from '@/domain/Storage'

export const useStorageItems = (folder: string) =>
  useQuery<StorageItem[]>({
    queryKey: ['storage', folder],
    queryFn: () => storageApi.list(folder),
    staleTime: 1000 * 30,
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
    mutationFn: (file: File) => storageApi.upload(file, folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export const useUploadFiles = (folder: string) => {
  const queryClient = useQueryClient()
  const [uploadingCount, setUploadingCount] = useState(0)

  const upload = useCallback(async (files: FileList | File[]) => {
    const list = Array.from(files)
    if (!list.length) return
    setUploadingCount(list.length)
    await Promise.allSettled(list.map(file => storageApi.upload(file, folder)))
    setUploadingCount(0)
    queryClient.invalidateQueries({ queryKey: ['storage', folder] })
  }, [folder, queryClient])

  return { upload, isUploading: uploadingCount > 0, uploadingCount }
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
