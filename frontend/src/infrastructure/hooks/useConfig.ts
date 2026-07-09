// frontend/src/infrastructure/hooks/useConfig.ts
import { useQuery } from '@tanstack/react-query'
import { reportApi } from '@/infrastructure/api/reportApi'
import type { AppConfig } from '@/domain/Config'

export const useConfig = () =>
  useQuery<AppConfig>({
    queryKey: ['config'],
    queryFn: reportApi.getConfig,
    staleTime: Infinity,
  })
