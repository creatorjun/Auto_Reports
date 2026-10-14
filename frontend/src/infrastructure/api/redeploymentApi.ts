// frontend/src/infrastructure/api/redeploymentApi.ts
import type { RedeploymentGateway } from '@/application/ports/ApplicationServices'
import client from './client'

export const redeploymentApi: RedeploymentGateway = {
  getLatest: async (signal) => (await client.get('/redeployments/latest', { signal })).data,
  generate: async () => (await client.post('/redeployments', undefined, { timeout: 600_000 })).data,
}
