// frontend/src/infrastructure/api/siteApi.ts
import client from './client'
import type {
  SiteDetail,
  SiteSummary,
  SiteCreatePayload,
  SiteUpdatePayload,
  DeploymentNodePayload,
  PatchHistoryPayload,
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

  update: async (id: number, payload: SiteUpdatePayload): Promise<SiteDetail> => {
    const res = await client.patch<SiteDetail>(`/sites/${id}`, payload)
    return res.data
  },

  addNode: async (siteId: number, payload: DeploymentNodePayload): Promise<SiteDetail> => {
    const res = await client.post<SiteDetail>(`/sites/${siteId}/nodes`, payload)
    return res.data
  },

  updateNode: async (siteId: number, nodeId: number, payload: DeploymentNodePayload): Promise<SiteDetail> => {
    const res = await client.patch<SiteDetail>(`/sites/${siteId}/nodes/${nodeId}`, payload)
    return res.data
  },

  deleteNode: async (siteId: number, nodeId: number): Promise<void> => {
    await client.delete(`/sites/${siteId}/nodes/${nodeId}`)
  },

  addPatchHistory: async (siteId: number, payload: PatchHistoryPayload): Promise<SiteDetail> => {
    const res = await client.post<SiteDetail>(`/sites/${siteId}/patch-histories`, payload)
    return res.data
  },

  updatePatchHistory: async (siteId: number, patchId: number, payload: PatchHistoryPayload): Promise<SiteDetail> => {
    const res = await client.patch<SiteDetail>(`/sites/${siteId}/patch-histories/${patchId}`, payload)
    return res.data
  },

  deletePatchHistory: async (siteId: number, patchId: number): Promise<void> => {
    await client.delete(`/sites/${siteId}/patch-histories/${patchId}`)
  },

  addVisitHistory: async (siteId: number, payload: VisitHistoryPayload): Promise<SiteDetail> => {
    const res = await client.post<SiteDetail>(`/sites/${siteId}/visit-histories`, payload)
    return res.data
  },

  updateVisitHistory: async (siteId: number, visitId: number, payload: VisitHistoryPayload): Promise<SiteDetail> => {
    const res = await client.patch<SiteDetail>(`/sites/${siteId}/visit-histories/${visitId}`, payload)
    return res.data
  },

  deleteVisitHistory: async (siteId: number, visitId: number): Promise<void> => {
    await client.delete(`/sites/${siteId}/visit-histories/${visitId}`)
  },
}
