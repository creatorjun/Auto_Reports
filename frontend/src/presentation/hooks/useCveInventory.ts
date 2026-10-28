// frontend/src/presentation/hooks/useCveInventory.ts
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { CveInventoryPackageRequest, CveInventoryRequest, CveInventorySnapshot } from '@/domain/CveInventory'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

export const CVE_INVENTORY_QUERY_KEY = ['cve-inventory'] as const
export const CVE_INVENTORY_PACKAGES_KEY = ['cve-inventory-packages'] as const

export function useCveInventory(request: CveInventoryRequest) {
  const { cveInventory } = useApplicationServices()
  const sessionVersion = useAuthStore((state) => state.sessionVersion)
  const queryClient = useQueryClient()
  const [now, setNow] = useState(Date.now)
  const refreshPending = useRef(false)
  const query = useQuery({
    queryKey: [...CVE_INVENTORY_QUERY_KEY, sessionVersion, request],
    queryFn: async ({ signal }) => {
      const data = await cveInventory.getSnapshot(request, signal)
      if (sessionVersion !== useAuthStore.getState().sessionVersion) throw new Error('Session changed')
      return data
    },
    staleTime: 15000,
    refetchInterval: (state) => state.state.data?.refreshing ? 2000 : 60000,
    refetchOnWindowFocus: true,
  })
  const mutation = useMutation({
    mutationFn: (version: number) => {
      if (version !== useAuthStore.getState().sessionVersion) throw new Error('Session changed')
      return cveInventory.refresh()
    },
    onSuccess: (snapshot, version) => {
      if (version !== useAuthStore.getState().sessionVersion) return
      queryClient.setQueriesData<CveInventorySnapshot>({ queryKey: [...CVE_INVENTORY_QUERY_KEY, version] }, (data) => data ? {
        ...data, refreshing: snapshot.refreshing, retry_after_seconds: snapshot.retry_after_seconds,
        next_refresh_at: snapshot.next_refresh_at, progress: snapshot.progress,
      } : data)
      void queryClient.invalidateQueries({ queryKey: [...CVE_INVENTORY_QUERY_KEY, version] })
      void queryClient.invalidateQueries({ queryKey: [...CVE_INVENTORY_PACKAGES_KEY, version] })
    },
    onSettled: () => { refreshPending.current = false },
  })
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const serverRetryAfterSeconds = Math.max(0, query.data?.retry_after_seconds ?? 0)
  const retryAfterSeconds = Math.min(serverRetryAfterSeconds, Math.max(0, Math.ceil((query.dataUpdatedAt + serverRetryAfterSeconds * 1000 - now) / 1000)))
  const refreshing = mutation.isPending || !!query.data?.refreshing
  const canRefresh = !refreshing && !query.isFetching && retryAfterSeconds === 0
  const refresh = () => {
    if (!canRefresh || refreshPending.current) return
    refreshPending.current = true
    mutation.mutate(sessionVersion)
  }
  return { ...query, refresh, refreshing, canRefresh, retryAfterSeconds, refreshError: mutation.error }
}

export function useCveInventoryPackages(request: CveInventoryPackageRequest, enabled: boolean) {
  const { cveInventory } = useApplicationServices()
  const sessionVersion = useAuthStore((state) => state.sessionVersion)
  return useQuery({
    queryKey: [...CVE_INVENTORY_PACKAGES_KEY, sessionVersion, request],
    queryFn: async ({ signal }) => {
      const data = await cveInventory.getPackages(request, signal)
      if (sessionVersion !== useAuthStore.getState().sessionVersion) throw new Error('Session changed')
      return data
    },
    enabled,
    staleTime: 15000,
    refetchInterval: enabled ? 15000 : false,
  })
}
