// frontend/src/infrastructure/api/cveInventoryApi.ts
import type { CveInventoryGateway } from '@/application/ports/ApplicationServices'
import client from './client'

export const cveInventoryApi: CveInventoryGateway = {
  getSnapshot: async (request, signal) => {
    const response = await client.get('/cve-inventory', { params: request, signal })
    return response.data
  },
  refresh: async () => {
    const response = await client.post('/cve-inventory/refresh')
    return response.data
  },
  getPackages: async (request, signal) => {
    const response = await client.get('/cve-inventory/packages', { params: request, signal })
    return response.data
  },
}
