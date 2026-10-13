// frontend/src/presentation/hooks/useAuditLogs.ts
import { useQuery } from '@tanstack/react-query'
import type { AuditLogQuery } from '@/domain/AuditLog'
import { canViewAuditLogs } from '@/domain/Auth'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { useMe } from './useAuth'

export function useAuditLogs(request: AuditLogQuery) {
  const { auditLogs } = useApplicationServices()
  const accessToken = useAuthStore((state) => state.accessToken)
  const me = useMe()
  const allowed = !!accessToken && !me.isError && canViewAuditLogs(me.data)
  const query = useQuery({
    queryKey: ['audit-logs', accessToken, request],
    queryFn: ({ signal }) => auditLogs.getLogs(request, signal),
    enabled: allowed,
    retry: false,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  })
  return { ...query, data: allowed && !query.isError ? query.data : undefined, allowed }
}
