// frontend/src/presentation/pages/LoginPage.tsx
import { useMutation, useQuery } from '@tanstack/react-query'
import { LogIn } from 'lucide-react'
import BrandLogo from '@/presentation/components/common/BrandLogo'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthSession } from '@/presentation/hooks/useAuthSession'
import { useAuthStore } from '@/presentation/state/authStore'
import { jiraLoginError } from '@/application/services/jiraLogin'

export default function LoginPage() {
  const { auth } = useApplicationServices()
  const [searchParams] = useSearchParams()
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

  if (isRestoring) return <LoadingSpinner text="로그인 확인 중..." />
  if (accessToken || !loginRequired) return <Navigate to="/" replace />

  return (
    <main className="min-h-screen flex items-center justify-center bg-apple-bg px-4 py-8">
      <div className="bg-apple-surface rounded-2xl shadow-sm border border-apple-divider/60 p-6 sm:p-8 w-full max-w-md">
        <div className="flex flex-col items-center gap-2 mb-8">
          <h1><BrandLogo className="w-64 max-w-full" /></h1>
        </div>

        <button
          type="button"
          onClick={() => jiraLogin.mutate()}
          disabled={jiraLogin.isPending || !providers.data?.jira.enabled}
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
        <footer className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-caption text-apple-light">
          <Link to="/privacy" className="hover:text-brand-600">개인정보처리방침</Link>
          <Link to="/terms" className="hover:text-brand-600">이용약관</Link>
        </footer>
      </div>
    </main>
  )
}
