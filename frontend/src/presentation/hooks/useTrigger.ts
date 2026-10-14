// frontend/src/presentation/hooks/useTrigger.ts
import { useQueryClient } from '@tanstack/react-query'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { useJobStream } from './useJobStream'
import type { TriggerParams } from '@/domain/Job'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { RequestError } from '@/application/errors/RequestError'

interface TriggerCallbacks {
  onComplete: (reportId: number | null) => void
  onError:    (message: string) => void
  onTimeout:  () => void
}

export const useTrigger = (callbacks?: TriggerCallbacks) => {
  const { reports } = useApplicationServices()
  const queryClient = useQueryClient()
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const failure = (error: unknown) => {
    if (error instanceof RequestError && typeof error.detail === 'string') return error.detail
    return '보고서 생성 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }
  const { start, stop } = useJobStream({
    onComplete: (reportId) => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      callbacks?.onComplete(reportId)
    },
    onError:   (msg)  => callbacks?.onError(msg),
    onTransportError: (error) => callbacks?.onError(failure(error)),
    onTimeout: ()     => callbacks?.onTimeout(),
  }, 600_000)

  return useMutation({
    mutationFn: (params: TriggerParams | void) => reports.trigger(params ?? undefined),
    onSuccess: (data) => { if (mountedRef.current) start(data.job_id) },
    onError: (error) => {
      stop()
      if (mountedRef.current) callbacks?.onError(failure(error))
    },
    retry: false,
  })
}
