// frontend/src/presentation/hooks/useSlaViolations.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { SlaViolationRequest } from '@/domain/SlaViolationReport'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

export const SLA_VIOLATION_KEYS = {
  latest: ['sla-violations', 'latest'] as const,
  history: ['sla-violations', 'history'] as const,
  report: (id: number) => ['sla-violations', 'report', id] as const,
}

export function useSlaViolationReport(id?: number) {
  const { slaViolations } = useApplicationServices()
  return useQuery({
    queryKey: id === undefined ? SLA_VIOLATION_KEYS.latest : SLA_VIOLATION_KEYS.report(id),
    queryFn: ({ signal }) => id === undefined ? slaViolations.getLatest(signal) : slaViolations.getById(id, signal),
    enabled: id === undefined || Number.isSafeInteger(id) && id > 0,
    staleTime: id === undefined ? 0 : Infinity,
    refetchOnMount: id === undefined ? 'always' : false,
    refetchOnWindowFocus: false,
    retry: 1,
  })
}

export function useSlaViolationHistory(page = 0, limit = 20) {
  const { slaViolations } = useApplicationServices()
  return useQuery({
    queryKey: [...SLA_VIOLATION_KEYS.history, page, limit],
    queryFn: ({ signal }) => slaViolations.getHistory(limit, page * limit, signal),
    staleTime: 0,
  })
}

export function useGenerateSlaViolationReport() {
  const { slaViolations } = useApplicationServices()
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: SlaViolationRequest) => slaViolations.generate(request),
    onMutate: async () => {
      const sessionVersion = useAuthStore.getState().sessionVersion
      await client.cancelQueries({ queryKey: SLA_VIOLATION_KEYS.latest })
      if (sessionVersion !== useAuthStore.getState().sessionVersion) throw new Error('Session changed')
      return sessionVersion
    },
    onSuccess: async (report, _, sessionVersion) => {
      if (sessionVersion !== useAuthStore.getState().sessionVersion) return
      await client.cancelQueries({ queryKey: SLA_VIOLATION_KEYS.latest })
      if (sessionVersion !== useAuthStore.getState().sessionVersion) return
      client.setQueryData(SLA_VIOLATION_KEYS.latest, report)
      client.setQueryData(SLA_VIOLATION_KEYS.report(report.id), report)
      await client.invalidateQueries({ queryKey: SLA_VIOLATION_KEYS.history })
    },
    retry: false,
  })
}
