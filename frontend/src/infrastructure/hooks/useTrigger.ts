import { useMutation, useQueryClient } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import { useUiStore } from '@/app/store/uiStore'

export const useTrigger = () => {
  const queryClient = useQueryClient()
  const { setTriggerLoading, setTriggerMessage } = useUiStore()

  return useMutation({
    mutationFn: reportApi.trigger,
    onMutate: () => {
      setTriggerLoading(true)
      setTriggerMessage(null)
    },
    onSuccess: (data) => {
      setTriggerMessage(data.message)
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
    onError: () => setTriggerMessage('보고서 생성에 실패했습니다.'),
    onSettled: () => setTriggerLoading(false)
  })
}
