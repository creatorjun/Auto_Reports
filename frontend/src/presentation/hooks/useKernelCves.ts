// frontend/src/presentation/hooks/useKernelCves.ts
import { useQuery } from '@tanstack/react-query'
import type { KernelBuild, UpstreamKernelRequest } from '@/domain/KernelCve'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { useCveSnapshot } from '@/presentation/hooks/useCveSnapshot'

export function useKernelTargets() {
  const { kernelCves } = useApplicationServices()
  const session = useAuthStore((state) => state.sessionVersion)
  return useQuery({
    queryKey: ['kernel-cves', session, 'targets'],
    queryFn: ({ signal }) => kernelCves.getTargets(signal),
    staleTime: 300_000,
    retry: false,
  })
}

export function useUpstreamKernelCves(request: UpstreamKernelRequest) {
  const { kernelCves } = useApplicationServices()
  return useCveSnapshot('kernel', 'upstream', request, (signal) => kernelCves.getUpstream(request, signal))
}

export function useKernelReleases(build: KernelBuild) {
  const { kernelCves } = useApplicationServices()
  return useCveSnapshot('kernel', 'releases', build, (signal) => kernelCves.getReleases(build, signal))
}
