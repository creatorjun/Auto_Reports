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

export interface JiraPrivacyStatus {
  owner_authorized: boolean
  registered_accounts: number
  unreported_accounts?: number
  due_accounts?: number
  account_states: Record<string, number>
  next_attempt_at: string | null
  last_success_at: string | null
  last_error: string | null
  coverage: {
    known_accounts: number
    unmapped_personal_fields: number
  }
  reporting_ready?: boolean
}

export function canViewAuditLogs(me: MeResponse | undefined): boolean {
  return me?.login_required === true && me.is_superadmin === true
}

export function canViewJiraNotifications(me: MeResponse | undefined): boolean {
  return me?.login_required === true && me.auth_provider === 'jira'
}

export function loginUserId(me: MeResponse | undefined): string | null {
  if (!me?.login_required) return null
  if (me.auth_provider === 'jira' && me.username.startsWith('jira:')) {
    return me.username.split(':').slice(2).join(':') || me.username
  }
  return me.username
}
