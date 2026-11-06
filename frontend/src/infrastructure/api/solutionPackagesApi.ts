// frontend/src/infrastructure/api/solutionPackagesApi.ts
import type { SolutionPackagesGateway } from '@/application/ports/ApplicationServices'
import type { SolutionPackageInventory } from '@/domain/SolutionPackages'
import client from './client'

export const solutionPackagesApi: SolutionPackagesGateway = {
  async list(product, version, signal) {
    const { data } = await client.get<SolutionPackageInventory>('/solution-packages', {
      params: version === null ? { product } : { product, version },
      signal,
    })
    return data
  },
}
