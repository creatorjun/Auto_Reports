// frontend/src/infrastructure/api/authApi.ts
import client from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface MeResponse {
  username: string
  login_required: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export const authApi = {
  login: async ({ username, password }: LoginRequest): Promise<TokenResponse> => {
    const res = await client.post<TokenResponse>('/auth/login', { username, password })
    return res.data
  },

  refresh: async (): Promise<TokenResponse> => {
    const res = await client.post<TokenResponse>('/auth/refresh')
    return res.data
  },

  logout: async (): Promise<void> => {
    await client.post('/auth/logout')
  },

  me: async (): Promise<MeResponse> => {
    const res = await client.get<MeResponse>('/auth/me')
    return res.data
  },
}
