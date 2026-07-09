// frontend/src/infrastructure/hooks/useTrigger.ts
import { useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import type { TriggerParams } from '@/infrastructure/api/reportApi'
import { useUiStore } from '@/app/store/uiStore'

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS = 180000

export const useTrigger = () => {
  const queryClient = useQueryClient()
  const { setTriggerLoading, setTriggerMessage } = useUiStore()
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsedRef = useRef(0)

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
        setTriggerLoading(false)
        setTriggerMessage('보고서 생성이 시간 초과되었습니다.')
        return
      }
      try {
        const status = await reportApi.getJobStatus(jobId)
        if (status.status === 'done') {
          stopPolling()
          setTriggerLoading(false)
          setTriggerMessage(`보고서 생성 완료 (ID: ${status.report_id})`)
          queryClient.invalidateQueries({ queryKey: ['reports'] })
        } else if (status.status === 'error') {
          stopPolling()
          setTriggerLoading(false)
          setTriggerMessage(`보고서 생성 실패: ${status.error ?? '알 수 없는 오류'}`)
        }
      } catch {
        stopPolling()
        setTriggerLoading(false)
        setTriggerMessage('상태 확인 중 오류가 발생했습니다.')
      }
    }, POLL_INTERVAL_MS)
  }

  return useMutation({
    mutationFn: (params: TriggerParams | void) => reportApi.trigger(params ?? undefined),
    onMutate: () => {
      setTriggerLoading(true)
      setTriggerMessage(null)
    },
    onSuccess: (data) => {
      startPolling(data.job_id)
    },
    onError: () => {
      setTriggerLoading(false)
      setTriggerMessage('보고서 생성 요청에 실패했습니다.')
    },
  })
}
