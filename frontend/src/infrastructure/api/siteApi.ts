// frontend/src/infrastructure/api/siteApi.ts
import client from './client'
import type { SiteDetail, SiteSummary, SiteCreatePayload } from '@/domain/Site'

export const siteApi = {
  search: async (q: string, limit = 10): Promise<SiteSummary[]> => {
    const res = await client.get<SiteSummary[]>('/sites/search', { params: { q, limit } })
    return res.data
  },

  getRecent: async (limit = 5): Promise<SiteSummary[]> => {
    const res = await client.get<SiteSummary[]>('/sites/recent', { params: { limit } })
    return res.data
  },

  getById: async (id: string): Promise<SiteDetail> => {
    const res = await client.get<SiteDetail>(`/sites/${id}`)
    return res.data
  },

  create: async (payload: SiteCreatePayload): Promise<{ id: string }> => {
    const res = await client.post<{ id: string }>('/sites/', payload)
    return res.data
  },
}
