// frontend/src/infrastructure/hooks/useTrigger.ts
import { useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import type { TriggerParams } from '@/domain/Job'

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS  = 180000

interface TriggerCallbacks {
  onComplete: (reportId: number | null) => void
  onError:    (message: string) => void
  onTimeout:  () => void
}

export const useTrigger = (callbacks?: TriggerCallbacks) => {
  const queryClient = useQueryClient()
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsedRef  = useRef(0)

  const stopPolling = () => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    elapsedRef.current = 0
  }

  const startPolling = (jobId: string) => {
    elapsedRef.current = 0
    timerRef.current = setInterval(async () => {
      elapsedRef.current += POLL_INTERVAL_MS
      if (elapsedRef.current >= POLL_TIMEOUT_MS) {
        stopPolling()
        callbacks?.onTimeout()
        return
      }
      try {
        const status = await reportApi.getJobStatus(jobId)
        if (status.status === 'done') {
          stopPolling()
          queryClient.invalidateQueries({ queryKey: ['reports'] })
          callbacks?.onComplete(status.report_id)
        } else if (status.status === 'error') {
          stopPolling()
          callbacks?.onError(status.error ?? '알 수 없는 오류')
        }
      } catch {
        stopPolling()
        callbacks?.onError('상태 확인 중 오류가 발생했습니다.')
      }
    }, POLL_INTERVAL_MS)
  }

  return useMutation({
    mutationFn: (params: TriggerParams | void) => reportApi.trigger(params ?? undefined),
    onSuccess: (data) => startPolling(data.job_id),
  })
}
