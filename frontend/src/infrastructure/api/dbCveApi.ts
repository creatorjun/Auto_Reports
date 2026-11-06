// frontend/src/infrastructure/api/dbCveApi.ts
import type { SoftwareCveGateway } from '@/application/ports/ApplicationServices'
import type { CveResults } from '@/domain/Cve'
import type { SoftwareReleases, SoftwareTarget } from '@/domain/SoftwareCve'
import client from './client'

export const dbCveApi: SoftwareCveGateway = {
  async getTargets(signal) {
    const { data } = await client.get<{ targets: SoftwareTarget[] }>('/db-cves/targets', { signal })
    return data.targets
  },
  async getReleases(target, signal) {
    const { data } = await client.get<SoftwareReleases>('/db-cves/releases', { params: { target }, signal })
    return data
  },
  async getFindings(params, signal) {
    const { data } = await client.get<CveResults>('/db-cves', { params, signal })
    return data
  },
}
