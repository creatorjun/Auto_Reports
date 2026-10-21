// frontend/src/application/services/storageUploads.ts
import type { CancellationSignal, StorageGateway, UploadSource } from '@/application/ports/ApplicationServices'

export interface UploadProgress {
  name: string
  percent: number
  done: boolean
  failed?: boolean
}

export class QuotaExceededError extends Error {
  constructor(public readonly available: number, public readonly needed: number) {
    super('QUOTA_EXCEEDED')
  }
}

export class UploadBatchError extends Error {
  constructor(public readonly failedNames: string[]) {
    super(`Upload failed: ${failedNames.join(', ')}`)
  }
}

function checkCancellation(signal?: CancellationSignal) {
  if (signal?.aborted) throw new Error('Upload cancelled')
}

export async function uploadStorageFiles(
  storage: Pick<StorageGateway, 'getQuota' | 'upload'>,
  files: UploadSource[],
  folder: string,
  overwrite: boolean,
  onProgress: (index: number, progress: UploadProgress) => void,
  signal?: CancellationSignal,
): Promise<void> {
  if (!files.length) return
  checkCancellation(signal)
  const quota = await storage.getQuota()
  checkCancellation(signal)
  const needed = files.reduce((total, file) => total + file.size, 0)
  if (needed > quota.available) throw new QuotaExceededError(quota.available, needed)
  const results = await Promise.allSettled(files.map(async (file, index) => {
    let percent = 0
    try {
      checkCancellation(signal)
      await storage.upload(file, folder, overwrite, (value) => {
        percent = value
        if (!signal?.aborted) onProgress(index, { name: file.name, percent, done: false })
      }, signal)
      checkCancellation(signal)
      onProgress(index, { name: file.name, percent: 100, done: true })
    } catch (error) {
      if (!signal?.aborted) onProgress(index, { name: file.name, percent, done: false, failed: true })
      throw error
    }
  }))
  checkCancellation(signal)
  const failedNames = files.filter((_, index) => results[index].status === 'rejected').map((file) => file.name)
  if (failedNames.length) throw new UploadBatchError(failedNames)
}
