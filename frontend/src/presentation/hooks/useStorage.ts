// frontend/src/presentation/hooks/useStorage.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback, useEffect, useRef } from 'react'
import type { UploadSource } from '@/application/ports/ApplicationServices'
import { UploadBatchError, uploadStorageFiles, type UploadProgress } from '@/application/services/storageUploads'
import type { StorageItem, StorageQuota } from '@/domain/Storage'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

function toUploadSource(file: File): UploadSource {
  return {
    name: file.name,
    size: file.size,
    mediaType: file.type,
    read: (start, end) => file.slice(start, end).arrayBuffer(),
  }
}

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

export const useDownloadStorageSelection = (folder: string) => {
  const { storage } = useApplicationServices()
  return useMutation({
    mutationFn: (names: string[]) => storage.downloadSelection(folder, names),
  })
}

export const useDeleteStorageSelection = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (names: string[]) => storage.deleteSelection(folder, names),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
      queryClient.invalidateQueries({ queryKey: ['storage-quota'] })
    },
  })
}

export const useUploadFile = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, overwrite }: { file: File; overwrite: boolean }) =>
      storage.upload(toUploadSource(file), folder, overwrite),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', folder] })
    },
  })
}

export interface DuplicateFile {
  file: File
  exists: boolean
}

export type FileProgress = UploadProgress
export { QuotaExceededError, UploadBatchError } from '@/application/services/storageUploads'

export const useUploadFiles = (folder: string) => {
  const { storage } = useApplicationServices()
  const queryClient = useQueryClient()
  const [progressList, setProgressList] = useState<FileProgress[]>([])
  const [isUploading, setUploading] = useState(false)
  const active = useRef(true)
  const operation = useRef<AbortController | null>(null)
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
      operation.current?.abort()
      operation.current = null
      if (resetTimer.current !== null) clearTimeout(resetTimer.current)
    }
  }, [])

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
    if (!files.length || operation.current || !active.current) return
    const controller = new AbortController()
    operation.current = controller
    const sessionVersion = useAuthStore.getState().sessionVersion
    const unsubscribe = useAuthStore.subscribe((state) => {
      if (state.sessionVersion !== sessionVersion) controller.abort()
    })
    controller.signal.addEventListener('abort', unsubscribe, { once: true })
    const current = () => active.current && operation.current === controller && !controller.signal.aborted
    if (resetTimer.current !== null) clearTimeout(resetTimer.current)
    resetTimer.current = null
    setUploading(true)
    setProgressList(files.map(f => ({ name: f.name, percent: 0, done: false })))
    let succeeded = false
    try {
      await uploadStorageFiles(storage, files.map(toUploadSource), folder, overwrite, (index, progress) => {
        if (current()) setProgressList((previous) => previous.map((item, position) => position === index ? progress : item))
      }, controller.signal)
      succeeded = true
    } catch (error) {
      if (!current()) return
      if (!(error instanceof UploadBatchError)) setProgressList([])
      throw error
    } finally {
      unsubscribe()
      controller.signal.removeEventListener('abort', unsubscribe)
      const accepted = current()
      if (active.current && operation.current === controller) {
        operation.current = null
        setUploading(false)
        if (!accepted) setProgressList([])
        if (accepted) {
          void queryClient.invalidateQueries({ queryKey: ['storage', folder] })
          void queryClient.invalidateQueries({ queryKey: ['storage-quota'] })
        }
        if (accepted && succeeded) resetTimer.current = setTimeout(() => {
          resetTimer.current = null
          if (active.current && operation.current === null) setProgressList([])
        }, 1200)
      }
    }
  }, [folder, queryClient, storage])

  const uploadingCount = isUploading ? progressList.filter(p => !p.done && !p.failed).length : 0
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
