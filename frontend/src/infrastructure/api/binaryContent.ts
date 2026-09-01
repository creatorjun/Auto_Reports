// frontend/src/infrastructure/api/binaryContent.ts
import type { BinaryContent } from '@/application/ports/ApplicationServices'

export function createBinaryContent(data: Blob): BinaryContent {
  return {
    read: () => data.arrayBuffer(),
    createObjectUrl: () => {
      const url = URL.createObjectURL(data)
      let active = true
      return {
        url,
        close: () => {
          if (!active) return
          active = false
          URL.revokeObjectURL(url)
        },
      }
    },
  }
}
