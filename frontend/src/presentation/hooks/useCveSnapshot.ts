// frontend/src/presentation/hooks/useCveSnapshot.ts
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { CveCoverage, CveCoverageStatus } from '@/domain/Cve'
import { useAuthStore } from '@/presentation/state/authStore'

type Snapshot = { status: CveCoverageStatus; refreshing: boolean } & ({ total: number | null } | Pick<CveCoverage, 'sources'>)

function hasSnapshot(data: Snapshot) {
  return 'total' in data ? data.total !== null : data.sources.some((source) => source.refreshed_at !== null)
}

export function useCveSnapshot<T extends Snapshot>(scope: 'kernel' | 'java' | 'db', kind: string, request: object, read: (signal: AbortSignal) => Promise<T>) {
  const session = useAuthStore((state) => state.sessionVersion)
  const client = useQueryClient()
  const key = [`${scope}-cves`, session, kind, request]
  return useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const data = await read(signal)
      const previous = client.getQueryData<T>(key)
      const updating = data.refreshing || data.status === 'pending' || data.status === 'error' || data.status === 'stale'
      if (updating && !hasSnapshot(data) && previous && hasSnapshot(previous)) {
        return { ...previous, status: 'stale' as const, refreshing: data.refreshing }
      }
      return data
    },
    refetchInterval: (query) => query.state.data?.refreshing ? 3000 : 60_000,
    refetchIntervalInBackground: false,
    staleTime: 60_000,
    retry: false,
  })
}
