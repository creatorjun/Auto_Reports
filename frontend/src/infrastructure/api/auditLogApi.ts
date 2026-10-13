// frontend/src/infrastructure/api/auditLogApi.ts
import type { AuditLogGateway } from '@/application/ports/ApplicationServices'
import client from './client'

export const auditLogApi: AuditLogGateway = {
  getLogs: async (query, signal) => {
    const response = await client.get('/audit-logs', { params: query, signal })
    return response.data
  },
}
