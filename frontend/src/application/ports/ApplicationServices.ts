// frontend/src/application/ports/ApplicationServices.ts
import type { AuthProviders, JiraLoginStartResponse, JiraPrivacyStatus, LoginRequest, MeResponse, TokenResponse } from '@/domain/Auth'
import type { AuditLogPage, AuditLogQuery } from '@/domain/AuditLog'
import type { AppConfig } from '@/domain/Config'
import type { IssueManagementSnapshot } from '@/domain/IssueManagement'
import type { DashboardPdfDocument } from '@/domain/DashboardExport'
import type { JobStatus, TriggerAccepted, TriggerParams } from '@/domain/Job'
import type { PartnerIssue, PartnerMember, PartnerOrg } from '@/domain/Partner'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { RedeploymentReport } from '@/domain/RedeploymentReport'
import type { ChartIssuesRequest, ChartIssuesResult } from '@/domain/ReportChartDetails'
import type { SearchResult } from '@/domain/Search'
import type { SecurityNewsSnapshot } from '@/domain/SecurityNews'
import type { SlaDashboardCommentPage, SlaDashboardIssue } from '@/domain/SlaDashboard'
import type { SlaViolationReport, SlaViolationReportSummary, SlaViolationRequest } from '@/domain/SlaViolationReport'
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
import type { PreviewParserPort } from '@/application/ports/PreviewParserPort'

export interface AuthGateway {
  login: (request: LoginRequest) => Promise<TokenResponse>
  providers: () => Promise<AuthProviders>
  startJira: () => Promise<JiraLoginStartResponse>
  getJiraPrivacyStatus: () => Promise<JiraPrivacyStatus>
  startJiraPrivacy: () => Promise<JiraLoginStartResponse>
  refresh: () => Promise<TokenResponse>
  logout: () => Promise<void>
  me: () => Promise<MeResponse>
}

export interface AuditLogGateway {
  getLogs: (query: AuditLogQuery, signal?: CancellationSignal) => Promise<AuditLogPage>
}

export interface JobStreamCallbacks {
  onStatus?: (status: JobStatus) => void
  onComplete: (reportId: number | null) => void
  onError: (message: string) => void
  onTransportError?: (error: unknown) => void
  onTimeout: () => void
}

export interface JobStreamSubscription {
  close: () => void
}

export interface BinaryContent {
  read: () => Promise<ArrayBuffer>
  createObjectUrl: () => BinaryObjectUrl
}

export interface BinaryObjectUrl {
  url: string
  close: () => void
}

export interface UploadSource {
  name: string
  size: number
  mediaType: string
  read: (start: number, end: number) => Promise<ArrayBuffer>
}

export interface CancellationSignal {
  readonly aborted: boolean
  addEventListener: (type: 'abort', listener: () => void) => void
  removeEventListener: (type: 'abort', listener: () => void) => void
}

export interface ReportGateway {
  getLatest: () => Promise<ReportDetail | null>
  getAnnual: (year: number) => Promise<ReportDetail>
  getById: (id: number) => Promise<ReportDetail>
  getChartIssues: (id: number, request: ChartIssuesRequest, signal?: CancellationSignal) => Promise<ChartIssuesResult>
  getAll: (limit?: number, offset?: number) => Promise<ReportSummary[]>
  trigger: (params?: TriggerParams) => Promise<TriggerAccepted>
  watchJob: (
    jobId: string,
    callbacks: JobStreamCallbacks,
    timeoutMs?: number,
  ) => JobStreamSubscription
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
  downloadSelection: (folder: string, names: string[]) => Promise<BinaryContent>
  deleteSelection: (folder: string, names: string[]) => Promise<void>
  upload: (
    file: UploadSource,
    folder?: string,
    overwrite?: boolean,
    onProgress?: (percent: number) => void,
  ) => Promise<StorageItem>
  readPreview: (name: string, folder?: string) => Promise<BinaryContent>
  convertPreview: (name: string, folder?: string) => Promise<BinaryContent>
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
    signal?: CancellationSignal,
  ) => Promise<SearchResult[]>
  getJiraBaseUrl: () => Promise<string>
}

export interface SlaDashboardGateway {
  getIssues: () => Promise<SlaDashboardIssue[]>
  getComments: (issueKey: string, offset?: number, limit?: number, reportId?: number) => Promise<SlaDashboardCommentPage>
  getCommentImage: (issueKey: string, commentId: string, attachmentId: string, reportId?: number) => Promise<BinaryContent>
}

export interface DashboardExportGateway {
  renderPdf: (document: DashboardPdfDocument) => Promise<BinaryContent>
  renderExcel: (document: DashboardPdfDocument) => Promise<BinaryContent>
}

export interface SlaViolationGateway {
  generate: (request: SlaViolationRequest) => Promise<SlaViolationReport>
  getLatest: (signal?: CancellationSignal) => Promise<SlaViolationReport | null>
  getById: (id: number, signal?: CancellationSignal) => Promise<SlaViolationReport>
  getHistory: (limit?: number, offset?: number, signal?: CancellationSignal) => Promise<SlaViolationReportSummary[]>
}

export interface ApplicationServices {
  previewParser: PreviewParserPort
  dashboardExport: DashboardExportGateway
  auth: AuthGateway
  auditLogs: AuditLogGateway
  reports: ReportGateway
  sites: SiteGateway
  storage: StorageGateway
  partners: PartnerGateway
  search: SearchGateway
  slaDashboard: SlaDashboardGateway
  slaViolations: SlaViolationGateway
  redeployments: RedeploymentGateway
  issueManagement: { getIssues: () => Promise<IssueManagementSnapshot> }
  securityNews: SecurityNewsGateway
}

export interface SecurityNewsGateway {
  getSnapshot: (signal?: CancellationSignal) => Promise<SecurityNewsSnapshot>
  refresh: () => Promise<SecurityNewsSnapshot>
}

export interface RedeploymentGateway {
  getLatest: (signal?: CancellationSignal) => Promise<RedeploymentReport | null>
  generate: () => Promise<RedeploymentReport>
}
