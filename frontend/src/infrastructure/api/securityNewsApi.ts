// frontend/src/infrastructure/api/securityNewsApi.ts
import type { SecurityNewsGateway } from '@/application/ports/ApplicationServices'
import client from './client'

export const securityNewsApi: SecurityNewsGateway = {
  getSnapshot: async (signal) => {
    const response = await client.get('/security-news', { signal })
    return response.data
  },
  refresh: async () => {
    const response = await client.post('/security-news/refresh')
    return response.data
  },
}
