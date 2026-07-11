// frontend/src/infrastructure/hooks/useTrigger.ts
import { useQueryClient } from '@tanstack/react-query'
import { useMutation } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import { useJobStream } from './useJobStream'
import type { TriggerParams } from '@/domain/Job'

interface TriggerCallbacks {
  onComplete: (reportId: number | null) => void
  onError:    (message: string) => void
  onTimeout:  () => void
}

export const useTrigger = (callbacks?: TriggerCallbacks) => {
  const queryClient = useQueryClient()

  const { start } = useJobStream({
    onComplete: (reportId) => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      callbacks?.onComplete(reportId)
    },
    onError:   (msg)  => callbacks?.onError(msg),
    onTimeout: ()     => callbacks?.onTimeout(),
  })

  return useMutation({
    mutationFn: (params: TriggerParams | void) => reportApi.trigger(params ?? undefined),
    onSuccess: (data) => start(data.job_id),
  })
}
