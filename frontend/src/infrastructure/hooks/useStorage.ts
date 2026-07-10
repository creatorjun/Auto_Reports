// frontend/src/infrastructure/hooks/useStorage.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { storageApi } from '@/infrastructure/api/storageApi'
import type { StorageFile } from '@/domain/Storage'

export const useStorageFiles = () =>
  useQuery<StorageFile[]>({
    queryKey: ['storage'],
    queryFn: storageApi.list,
    staleTime: 1000 * 30,
  })

export const useUploadFile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => storageApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage'] })
    },
  })
}

export const useDeleteStorageFile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (filename: string) => storageApi.delete(filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage'] })
    },
  })
}
