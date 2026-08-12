// frontend/src/presentation/hooks/useConfig.ts
import { useQuery } from '@tanstack/react-query'
import type { AppConfig } from '@/domain/Config'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export const useConfig = () => {
  const { reports } = useApplicationServices()
  return useQuery<AppConfig>({
    queryKey: ['config'],
    queryFn: reports.getConfig,
    staleTime: Infinity,
  })
}
