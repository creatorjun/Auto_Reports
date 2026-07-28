// frontend/src/infrastructure/api/siteApi.ts
import client from './client'
import type {
  SiteDetail,
  SiteSummary,
  SiteCreatePayload,
  PatchHistory,
  PatchHistoryPayload,
  VisitHistory,
  VisitHistoryPayload,
} from '@/domain/Site'

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

  create: async (payload: SiteCreatePayload): Promise<SiteDetail> => {
    const res = await client.post<SiteDetail>('/sites/', payload)
    return res.data
  },

  update: async (id: number, payload: Partial<SiteCreatePayload>): Promise<SiteDetail> => {
    const res = await client.put<SiteDetail>(`/sites/${id}`, payload)
    return res.data
  },

  addPatchHistory: async (siteId: number, payload: PatchHistoryPayload): Promise<PatchHistory> => {
    const res = await client.post<PatchHistory>(`/sites/${siteId}/patch_histories`, payload)
    return res.data
  },

  updatePatchHistory: async (siteId: number, patchId: number, payload: PatchHistoryPayload): Promise<PatchHistory> => {
    const res = await client.put<PatchHistory>(`/sites/${siteId}/patch_histories/${patchId}`, payload)
    return res.data
  },

  deletePatchHistory: async (siteId: number, patchId: number): Promise<void> => {
    await client.delete(`/sites/${siteId}/patch_histories/${patchId}`)
  },

  addVisitHistory: async (siteId: number, payload: VisitHistoryPayload): Promise<VisitHistory> => {
    const res = await client.post<VisitHistory>(`/sites/${siteId}/visit_histories`, payload)
    return res.data
  },

  updateVisitHistory: async (siteId: number, visitId: number, payload: VisitHistoryPayload): Promise<VisitHistory> => {
    const res = await client.put<VisitHistory>(`/sites/${siteId}/visit_histories/${visitId}`, payload)
    return res.data
  },

  deleteVisitHistory: async (siteId: number, visitId: number): Promise<void> => {
    await client.delete(`/sites/${siteId}/visit_histories/${visitId}`)
  },
}
