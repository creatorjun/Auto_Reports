// frontend/src/infrastructure/api/slaStatusApi.ts
import type { SlaStatusGateway } from '@/application/ports/ApplicationServices'
import type { SlaStatusSnapshot } from '@/domain/SLAStatus'
import client from './client'

export const slaStatusApi: SlaStatusGateway = {
  getSnapshot: async (refresh = false, signal) => {
    const response = await client.get<SlaStatusSnapshot>('/sla-status', { params: refresh ? { refresh: true } : undefined, signal, timeout: 120_000 })
    return response.data
  },
}
