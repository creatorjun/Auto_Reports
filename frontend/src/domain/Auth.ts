// frontend/src/domain/Auth.ts
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface MeResponse {
  username: string
  login_required: boolean
  is_superadmin: boolean
}

export function canViewAuditLogs(me: MeResponse | undefined): boolean {
  return me?.login_required === true && me.is_superadmin === true
}
