// frontend/src/presentation/pages/LoginPage.tsx
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { LogIn } from 'lucide-react'
import BrandLogo from '@/presentation/components/common/BrandLogo'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useLogin } from '@/presentation/hooks/useAuth'
import { useAuthSession } from '@/presentation/hooks/useAuthSession'
import { useAuthStore } from '@/presentation/state/authStore'
import { jiraLoginError } from '@/application/services/jiraLogin'

export default function LoginPage() {
  const { auth } = useApplicationServices()
  const [searchParams] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { mutate: login, isPending, isError } = useLogin()
  const { isRestoring } = useAuthSession()
  const { accessToken, loginRequired } = useAuthStore()
  const providers = useQuery({
    queryKey: ['auth-providers'],
    queryFn: auth.providers,
    staleTime: 60_000,
    retry: false,
  })
  const jiraLogin = useMutation({
    mutationFn: auth.startJira,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
  })
  const callbackError = jiraLoginError(searchParams.get('jira'))
  const busy = isPending || jiraLogin.isPending

  if (isRestoring) return <LoadingSpinner text="로그인 확인 중..." />
  if (accessToken || !loginRequired) return <Navigate to="/" replace />

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    login({ username, password })
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-apple-bg px-4 py-8">
      <div className="bg-apple-surface rounded-2xl shadow-sm border border-apple-divider/60 p-6 sm:p-8 w-full max-w-md">
        <div className="flex flex-col items-center gap-2 mb-8">
          <h1><BrandLogo className="w-64 max-w-full" /></h1>
        </div>

        <button
          type="button"
          onClick={() => jiraLogin.mutate()}
          disabled={busy || !providers.data?.jira.enabled}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-control font-medium text-white transition-colors hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <LogIn size={20} aria-hidden="true" className="shrink-0" />
          {jiraLogin.isPending ? 'Jira로 이동 중...' : 'Jira 계정으로 로그인'}
        </button>
        {providers.isPending && <p className="mt-3 text-center text-caption text-apple-light" role="status">로그인 방법 확인 중...</p>}
        {providers.data && !providers.data.jira.enabled && <p className="mt-3 text-center text-caption text-apple-light">Jira 로그인 연동 설정이 필요합니다.</p>}
        {(providers.isError || jiraLogin.isError || callbackError) && (
          <p className="mt-3 text-center text-caption text-red-500" role="alert">
            {callbackError || 'Jira 로그인에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.'}
          </p>
        )}

        <div className="my-6 flex items-center gap-3 text-caption text-apple-light">
          <span className="h-px flex-1 bg-apple-divider" />
          <span>관리자 계정 로그인</span>
          <span className="h-px flex-1 bg-apple-divider" />
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3" aria-label="관리자 로그인">
          <label className="sr-only" htmlFor="login-username">아이디</label>
          <input
            id="login-username"
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            disabled={busy}
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-control
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />
          <label className="sr-only" htmlFor="login-password">비밀번호</label>
          <input
            id="login-password"
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            disabled={busy}
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-control
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />

          {isError && (
            <p className="text-caption text-red-500 text-center" role="alert">아이디 또는 비밀번호를 확인하세요.</p>
          )}

          <button
            type="submit"
            disabled={busy || !username || !password}
            className="mt-1 w-full py-2.5 rounded-xl border border-apple-divider bg-apple-bg hover:bg-apple-divider/40 text-apple-dark text-control font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPending ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </main>
  )
}
