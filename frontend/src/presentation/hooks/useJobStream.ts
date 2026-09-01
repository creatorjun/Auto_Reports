// frontend/src/presentation/hooks/useJobStream.ts
import { useCallback, useEffect, useRef } from 'react'
import type {
  JobStreamCallbacks,
  JobStreamSubscription,
} from '@/application/ports/ApplicationServices'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export function useJobStream(callbacks: JobStreamCallbacks, timeoutMs?: number) {
  const { reports } = useApplicationServices()
  const subscriptionRef = useRef<JobStreamSubscription | null>(null)
  const callbacksRef = useRef(callbacks)

  useEffect(() => {
    callbacksRef.current = callbacks
  })

  const stop = useCallback(() => {
    subscriptionRef.current?.close()
    subscriptionRef.current = null
  }, [])

  const start = useCallback((jobId: string) => {
    stop()
    subscriptionRef.current = reports.watchJob(jobId, {
      onStatus: (status) => callbacksRef.current.onStatus?.(status),
      onComplete: (reportId) => callbacksRef.current.onComplete(reportId),
      onError: (message) => callbacksRef.current.onError(message),
      onTransportError: (error) => callbacksRef.current.onTransportError?.(error),
      onTimeout: () => callbacksRef.current.onTimeout(),
    }, timeoutMs)
  }, [reports, stop, timeoutMs])

  useEffect(() => () => stop(), [stop])

  return { start, stop }
}
