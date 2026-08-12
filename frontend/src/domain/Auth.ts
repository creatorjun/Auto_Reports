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
}
