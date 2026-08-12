// frontend/src/presentation/hooks/useJobStream.ts
import { useCallback, useEffect, useRef } from 'react'
import type { JobStatus } from '@/domain/Job'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

const EB_BASE_MS  = 1_000
const EB_MAX_MS   = 16_000
const EB_JITTER   = 0.2
const TIMEOUT_MS  = 300_000

interface JobStreamCallbacks {
  onStatus?:   (s: JobStatus) => void
  onComplete:  (reportId: number | null) => void
  onError:     (message: string) => void
  onTimeout:   () => void
}

function nextDelay(attempt: number): number {
  const base    = Math.min(EB_BASE_MS * 2 ** attempt, EB_MAX_MS)
  const jitter  = base * EB_JITTER * (Math.random() * 2 - 1)
  return Math.round(base + jitter)
}

export function useJobStream(callbacks: JobStreamCallbacks) {
  const { reports } = useApplicationServices()
  const esRef          = useRef<EventSource | null>(null)
  const timerRef       = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptRef     = useRef(0)
  const elapsedRef     = useRef(0)
  const activeRef      = useRef(false)
  const callbacksRef   = useRef(callbacks)

  useEffect(() => {
    callbacksRef.current = callbacks
  })

  const stop = useCallback(() => {
    activeRef.current = false
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const startExpBackoffPoll = useCallback((jobId: string) => {
    const tick = async () => {
      if (!activeRef.current) return

      if (elapsedRef.current >= TIMEOUT_MS) {
        stop()
        callbacksRef.current.onTimeout()
        return
      }

      try {
        const status = await reports.getJobStatus(jobId)
        callbacksRef.current.onStatus?.(status)

        if (status.status === 'done') {
          stop()
          callbacksRef.current.onComplete(status.report_id)
          return
        }
        if (status.status === 'error') {
          stop()
          callbacksRef.current.onError(status.error ?? '알 수 없는 오류')
          return
        }

        const serverHint = (status as JobStatus & { retry_after?: number }).retry_after
        const delay      = serverHint ? serverHint * 1000 : nextDelay(attemptRef.current)
        attemptRef.current  += 1
        elapsedRef.current  += delay
        timerRef.current = setTimeout(tick, delay)
      } catch {
        stop()
        callbacksRef.current.onError('상태 확인 중 오류가 발생했습니다.')
      }
    }

    tick()
  }, [reports, stop])

  const startSSE = useCallback((jobId: string) => {
    const token = useAuthStore.getState().accessToken
    const url   = reports.getJobStreamUrl(jobId, token ?? undefined)

    if (typeof EventSource === 'undefined') {
      startExpBackoffPoll(jobId)
      return
    }

    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('status', (e: MessageEvent) => {
      try {
        const data: JobStatus = JSON.parse(e.data)
        callbacksRef.current.onStatus?.(data)
      } catch {}
    })

    es.addEventListener('done', (e: MessageEvent) => {
      try {
        const data: JobStatus = JSON.parse(e.data)
        stop()
        if (data.status === 'error') {
          callbacksRef.current.onError(data.error ?? '알 수 없는 오류')
        } else {
          callbacksRef.current.onComplete(data.report_id)
        }
      } catch {
        stop()
        callbacksRef.current.onError('스트림 데이터 파싱 오류')
      }
    })

    es.addEventListener('timeout', () => {
      stop()
      callbacksRef.current.onTimeout()
    })

    es.addEventListener('error', () => {
      es.close()
      esRef.current = null
      startExpBackoffPoll(jobId)
    })
  }, [reports, startExpBackoffPoll, stop])

  const start = useCallback((jobId: string) => {
    stop()
    activeRef.current  = true
    attemptRef.current = 0
    elapsedRef.current = 0
    startSSE(jobId)
  }, [startSSE, stop])

  useEffect(() => () => { stop() }, [stop])

  return { start, stop }
}
