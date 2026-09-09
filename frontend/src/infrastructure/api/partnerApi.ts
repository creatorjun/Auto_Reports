// frontend/src/infrastructure/api/partnerApi.ts
import client from './client'
import type { PartnerOrg, PartnerMember, PartnerIssue } from '@/domain/Partner'

interface OrgsResponse    { organizations: Array<Omit<PartnerOrg, 'issue_count'> & { issue_count?: number }> }
interface MembersResponse { org_id: string; members: PartnerMember[] }
interface IssuesResponse  { issues: PartnerIssue[]; total: number }

export const partnerApi = {
  getOrganizations: async (): Promise<PartnerOrg[]> => {
    const res = await client.get<OrgsResponse>('/partners/organizations')
    return res.data.organizations.map((organization) => ({
      ...organization,
      issue_count: Number.isFinite(organization.issue_count) ? organization.issue_count! : 0,
    }))
  },

  getMembers: async (orgId: string): Promise<PartnerMember[]> => {
    const res = await client.get<MembersResponse>(`/partners/organizations/${orgId}/members`)
    return res.data.members
  },

  getIssuesByOrg: async (orgId: string): Promise<PartnerIssue[]> => {
    const res = await client.get<IssuesResponse>('/partners/issues', { params: { org_id: orgId } })
    return res.data.issues
  },

  getIssuesByMember: async (accountId: string): Promise<PartnerIssue[]> => {
    const res = await client.get<IssuesResponse>('/partners/issues', { params: { account_id: accountId } })
    return res.data.issues
  },
}
