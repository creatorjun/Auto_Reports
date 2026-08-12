// frontend/src/application/ports/AuthSessionPort.ts
export interface AuthSessionPort {
  getAccessToken: () => string | null
  getUsername: () => string | null
  setAuth: (token: string, username: string) => void
  clearAuth: () => void
  redirectToLogin: () => void
}
