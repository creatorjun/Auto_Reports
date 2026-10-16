// frontend/src/infrastructure/api/authApi.ts
import client, { endAuthSession, refreshAuthSession, startAuthSession } from './client'
import type { AuthProviders, JiraLoginStartResponse, JiraPrivacyStatus, LoginRequest, MeResponse, TokenResponse } from '@/domain/Auth'

export const authApi = {
  login: async ({ username, password }: LoginRequest): Promise<TokenResponse> => {
    return startAuthSession(async () => {
      const res = await client.post<TokenResponse>('/auth/login', { username, password })
      return res.data
    })
  },

  refresh: async (): Promise<TokenResponse> => {
    return refreshAuthSession()
  },

  logout: async (): Promise<void> => {
    return endAuthSession(async () => { await client.post('/auth/logout') })
  },

  me: async (): Promise<MeResponse> => {
    const res = await client.get<MeResponse>('/auth/me')
    return res.data
  },

  providers: async (): Promise<AuthProviders> => {
    const res = await client.get<AuthProviders>('/auth/providers')
    return res.data
  },

  startJira: async (): Promise<JiraLoginStartResponse> => {
    return startAuthSession(async () => {
      const res = await client.post<JiraLoginStartResponse>('/auth/jira/start')
      return res.data
    })
  },

  getJiraPrivacyStatus: async (): Promise<JiraPrivacyStatus> => {
    const res = await client.get<JiraPrivacyStatus>('/auth/jira/privacy/status')
    return res.data
  },

  startJiraPrivacy: async (): Promise<JiraLoginStartResponse> => {
    const res = await client.post<JiraLoginStartResponse>('/auth/jira/privacy/start')
    return res.data
  },
}
