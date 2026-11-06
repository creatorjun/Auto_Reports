// frontend/src/infrastructure/api/kernelCveApi.ts
import type { KernelCveGateway } from '@/application/ports/ApplicationServices'
import type { KernelCveResults, KernelReleases, KernelTarget, UpstreamKernelResults } from '@/domain/KernelCve'
import client from './client'

export const kernelCveApi: KernelCveGateway = {
  async getTargets(signal) {
    const { data } = await client.get<{ targets: KernelTarget[] }>('/kernel-cves/targets', { signal })
    return data.targets
  },
  async getReleases(params, signal) {
    const { data } = await client.get<KernelReleases>('/kernel-cves/releases', { params, signal })
    return data
  },
  async getFindings(params, signal) {
    const { data } = await client.get<KernelCveResults>('/kernel-cves', { params, signal })
    return data
  },
  async getUpstream(params, signal) {
    const { data } = await client.get<UpstreamKernelResults>('/kernel-cves/upstream', { params, signal })
    return data
  },
}
