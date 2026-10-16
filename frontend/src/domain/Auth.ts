// frontend/src/domain/Auth.ts
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  username?: string
  display_name?: string
  auth_provider?: 'local' | 'jira'
  is_superadmin?: boolean
}

export interface MeResponse {
  username: string
  login_required: boolean
  is_superadmin: boolean
  display_name?: string
  auth_provider?: 'local' | 'jira'
}

export interface AuthProviders {
  jira: { enabled: boolean }
}

export interface JiraLoginStartResponse {
  authorization_url: string
}

export function canViewAuditLogs(me: MeResponse | undefined): boolean {
  return me?.login_required === true && me.is_superadmin === true
}
