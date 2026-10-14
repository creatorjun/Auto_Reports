// frontend/src/infrastructure/api/slaViolationApi.ts
import type { SlaViolationGateway } from '@/application/ports/ApplicationServices'
import client from './client'

export const slaViolationApi: SlaViolationGateway = {
  generate: async (request) => {
    const response = await client.post('/sla-violations', request, { timeout: 600_000 })
    return response.data
  },
  getLatest: async (signal) => {
    const response = await client.get('/sla-violations/latest', { signal })
    return response.data
  },
  getById: async (id, signal) => {
    const response = await client.get(`/sla-violations/${id}`, { signal })
    return response.data
  },
  getHistory: async (limit = 20, offset = 0, signal) => {
    const response = await client.get('/sla-violations/history', { params: { limit, offset }, signal })
    return response.data
  },
}
