// frontend/src/presentation/pages/LoginPage.tsx
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useLogin } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { mutate: login, isPending, isError } = useLogin()
  const { accessToken } = useAuthStore()

  if (accessToken) return <Navigate to="/" replace />

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    login({ username, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-apple-bg">
      <div className="bg-white rounded-2xl shadow-sm border border-apple-divider/60 p-8 w-full max-w-sm">
        <div className="flex flex-col items-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1.2" fill="white" />
              <rect x="8" y="1" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="1" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="8" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.4" />
            </svg>
          </div>
          <h1 className="text-[18px] font-bold text-apple-dark tracking-tight">TAC 보고서</h1>
          <p className="text-[12px] text-apple-light">로그인이 필요합니다</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-[13px]
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-[13px]
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />

          {isError && (
            <p className="text-[12px] text-red-500 text-center">아이디 또는 비밀번호를 확인하세요.</p>
          )}

          <button
            type="submit"
            disabled={isPending || !username || !password}
            className="mt-1 w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700
                       text-white text-[13px] font-medium transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPending ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </div>
  )
}
