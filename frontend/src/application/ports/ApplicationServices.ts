// frontend/src/application/ports/ApplicationServices.ts
import type { LoginRequest, MeResponse, TokenResponse } from '@/domain/Auth'
import type { AppConfig } from '@/domain/Config'
import type { JobStatus, TriggerAccepted, TriggerParams } from '@/domain/Job'
import type { PartnerIssue, PartnerMember, PartnerOrg } from '@/domain/Partner'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { SearchResult } from '@/domain/Search'
import type { SlaDashboardComment, SlaDashboardIssue } from '@/domain/SlaDashboard'
import type {
  DeploymentNodePayload,
  PatchHistoryPayload,
  SiteCreatePayload,
  SiteDetail,
  SiteSummary,
  SiteUpdatePayload,
  VisitHistoryPayload,
} from '@/domain/Site'
import type { StorageItem, StorageQuota } from '@/domain/Storage'

export interface AuthGateway {
  login: (request: LoginRequest) => Promise<TokenResponse>
  refresh: () => Promise<TokenResponse>
  logout: () => Promise<void>
  me: () => Promise<MeResponse>
}

export interface ReportGateway {
  getLatest: () => Promise<ReportDetail | null>
  getAnnual: (year: number) => Promise<ReportDetail>
  getById: (id: number) => Promise<ReportDetail>
  getAll: (limit?: number, offset?: number) => Promise<ReportSummary[]>
  trigger: (params?: TriggerParams) => Promise<TriggerAccepted>
  getJobStatus: (jobId: string) => Promise<JobStatus>
  getJobStreamUrl: (jobId: string, token?: string) => string
  delete: (id: number) => Promise<void>
  getConfig: () => Promise<AppConfig>
}

export interface SiteGateway {
  search: (query: string, limit?: number) => Promise<SiteSummary[]>
  getRecent: (limit?: number) => Promise<SiteSummary[]>
  getById: (id: string) => Promise<SiteDetail>
  create: (payload: SiteCreatePayload) => Promise<SiteDetail>
  update: (id: number, payload: SiteUpdatePayload) => Promise<SiteDetail>
  addNode: (siteId: number, payload: DeploymentNodePayload) => Promise<SiteDetail>
  updateNode: (siteId: number, nodeId: number, payload: DeploymentNodePayload) => Promise<SiteDetail>
  deleteNode: (siteId: number, nodeId: number) => Promise<void>
  addPatchHistory: (siteId: number, payload: PatchHistoryPayload) => Promise<SiteDetail>
  updatePatchHistory: (siteId: number, patchId: number, payload: PatchHistoryPayload) => Promise<SiteDetail>
  deletePatchHistory: (siteId: number, patchId: number) => Promise<void>
  addVisitHistory: (siteId: number, payload: VisitHistoryPayload) => Promise<SiteDetail>
  updateVisitHistory: (siteId: number, visitId: number, payload: VisitHistoryPayload) => Promise<SiteDetail>
  deleteVisitHistory: (siteId: number, visitId: number) => Promise<void>
}

export interface StorageGateway {
  list: (folder?: string) => Promise<StorageItem[]>
  checkExists: (name: string, folder?: string) => Promise<boolean>
  getQuota: () => Promise<StorageQuota>
  createFolder: (name: string, folder?: string) => Promise<void>
  deleteFolder: (name: string, folder?: string) => Promise<void>
  move: (name: string, sourceFolder: string, destinationFolder: string) => Promise<void>
  downloadSelection: (folder: string, names: string[]) => Promise<Blob>
  deleteSelection: (folder: string, names: string[]) => Promise<void>
  upload: (
    file: File,
    folder?: string,
    overwrite?: boolean,
    onProgress?: (percent: number) => void,
  ) => Promise<StorageItem>
  preview: (name: string, folder?: string) => string
  download: (name: string, folder?: string) => string
  deleteFile: (name: string, folder?: string) => Promise<void>
}

export interface PartnerGateway {
  getOrganizations: () => Promise<PartnerOrg[]>
  getMembers: (orgId: string) => Promise<PartnerMember[]>
  getIssuesByOrg: (orgId: string) => Promise<PartnerIssue[]>
  getIssuesByMember: (accountId: string) => Promise<PartnerIssue[]>
}

export interface SearchGateway {
  search: (
    query: string,
    limit?: number,
    signal?: AbortSignal,
  ) => Promise<SearchResult[]>
  getJiraBaseUrl: () => Promise<string>
}

export interface SlaDashboardGateway {
  getIssues: () => Promise<SlaDashboardIssue[]>
  getComments: (issueKey: string) => Promise<SlaDashboardComment[]>
  getCommentImage: (issueKey: string, commentId: string, attachmentId: string) => Promise<Blob>
}

export interface ApplicationServices {
  auth: AuthGateway
  reports: ReportGateway
  sites: SiteGateway
  storage: StorageGateway
  partners: PartnerGateway
  search: SearchGateway
  slaDashboard: SlaDashboardGateway
}
