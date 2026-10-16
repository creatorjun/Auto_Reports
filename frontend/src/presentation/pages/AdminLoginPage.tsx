// frontend/src/presentation/pages/AdminLoginPage.tsx
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import BrandLogo from '@/presentation/components/common/BrandLogo'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { useLogin } from '@/presentation/hooks/useAuth'
import { useAuthSession } from '@/presentation/hooks/useAuthSession'

export default function AdminLoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { mutate: login, isPending, isError } = useLogin()
  const { accessToken, loginRequired, isRestoring } = useAuthSession()

  if (isRestoring) return <LoadingSpinner text="로그인 확인 중..." />
  if (accessToken || !loginRequired) return <Navigate to="/" replace />

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    login({ username, password })
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-apple-bg px-4 py-8">
      <div className="bg-apple-surface rounded-2xl shadow-sm border border-apple-divider/60 p-6 sm:p-8 w-full max-w-md">
        <div className="flex flex-col items-center gap-4 mb-8">
          <h1><BrandLogo className="w-64 max-w-full" /></h1>
          <p className="text-control font-medium text-apple-dark">관리자 로그인</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3" aria-label="관리자 로그인">
          <label className="sr-only" htmlFor="admin-username">아이디</label>
          <input
            id="admin-username"
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
            disabled={isPending}
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-control
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />
          <label className="sr-only" htmlFor="admin-password">비밀번호</label>
          <input
            id="admin-password"
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
            disabled={isPending}
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-control
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />
          {isError && (
            <p className="text-caption text-red-500 text-center" role="alert">아이디 또는 비밀번호를 확인하세요.</p>
          )}
          <button
            type="submit"
            disabled={isPending || !username || !password}
            className="mt-1 w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-control font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPending ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </main>
  )
}
