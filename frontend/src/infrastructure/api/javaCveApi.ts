// frontend/src/infrastructure/api/javaCveApi.ts
import type { SoftwareCveGateway } from '@/application/ports/ApplicationServices'
import type { CveResults } from '@/domain/Cve'
import type { SoftwareRelease, SoftwareReleases, SoftwareTarget } from '@/domain/SoftwareCve'
import client from './client'

type JavaRelease = Omit<SoftwareRelease, 'series'> & { major: number }
type JavaReleases = Omit<SoftwareReleases, 'versions'> & { versions: JavaRelease[] }

export const javaCveApi: SoftwareCveGateway = {
  async getTargets(signal) {
    const { data } = await client.get<{ targets: SoftwareTarget[] }>('/java-cves/targets', { signal })
    return data.targets
  },
  async getReleases(target, signal) {
    const { data } = await client.get<JavaReleases>('/java-cves/releases', { params: { target }, signal })
    return { ...data, versions: data.versions.map(({ major, ...build }) => ({ ...build, series: String(major) })) }
  },
  async getFindings(params, signal) {
    const { data } = await client.get<CveResults>('/java-cves', { params, signal })
    return data
  },
}
