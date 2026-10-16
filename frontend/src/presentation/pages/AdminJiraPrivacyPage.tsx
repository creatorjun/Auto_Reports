// frontend/src/presentation/pages/AdminJiraPrivacyPage.tsx
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import BrandLogo from '@/presentation/components/common/BrandLogo'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useMe } from '@/presentation/hooks/useAuth'
import { useAuthSession } from '@/presentation/hooks/useAuthSession'

function displayTime(value: string | null | undefined, empty = '기록 없음'): string {
  if (!value) return empty
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '확인 필요'
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul', dateStyle: 'medium', timeStyle: 'short',
  }).format(date)
}

function PrivacyConnection({ accessToken }: { accessToken: string }) {
  const { auth } = useApplicationServices()
  const [searchParams] = useSearchParams()
  const status = useQuery({
    queryKey: ['jira-privacy-status', accessToken],
    queryFn: auth.getJiraPrivacyStatus,
    retry: false,
    gcTime: 0,
    refetchOnWindowFocus: false,
  })
  const connect = useMutation({
    mutationFn: auth.startJiraPrivacy,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
  })
  const callback = searchParams.get('jira_privacy')
  const data = status.data
  const pending = (data?.account_states.pending_updated ?? 0) + (data?.account_states.pending_closed ?? 0)

  return (
    <>
      <div className="rounded-xl border border-apple-divider bg-apple-gray/40 p-4 text-body leading-relaxed text-apple-mid">
        <p>앱 소유자의 Atlassian 계정으로 개인정보 정기 보고 연결을 승인합니다. 사용자 정보 조회와 <span className="break-all font-medium">offline_access</span> 권한을 요청하며, 정기 보고에 필요한 인증 토큰은 서버에서 암호화해 보관합니다.</p>
        <p className="mt-2">이 연결은 직원의 Jira 로그인 승인 범위를 변경하지 않습니다. 관리자 로그인은 유지됩니다.</p>
      </div>

      {callback === 'success' && <p className="mt-4 text-body text-brand-600" role="status">개인정보 보고 연결이 완료되었습니다.</p>}
      {(callback === 'denied' || callback === 'unavailable' || callback === 'error') && (
        <p className="mt-4 text-body text-red-500" role="alert">연결을 완료하지 못했습니다. 앱 소유자 계정과 승인 여부를 확인한 뒤 다시 시도해 주세요.</p>
      )}

      {status.isPending && <div className="py-6"><LoadingSpinner text="보고 연결 상태 확인 중..." /></div>}
      {status.isError && <p className="mt-4 text-body text-red-500" role="alert">보고 연결 상태를 확인하지 못했습니다.</p>}
      {data && (
        <dl className="my-6 grid gap-4 rounded-xl border border-apple-divider p-4 sm:grid-cols-2">
          <div><dt className="text-caption text-apple-light">연결 상태</dt><dd className="mt-1 text-body font-medium text-apple-dark">{data.owner_authorized ? '연결됨' : '연결 안 됨'}</dd></div>
          <div><dt className="text-caption text-apple-light">등록 계정</dt><dd className="mt-1 text-body font-medium text-apple-dark">{data.registered_accounts.toLocaleString()}개</dd></div>
          {data.due_accounts !== undefined && <div><dt className="text-caption text-apple-light">정기 보고 대기</dt><dd className="mt-1 text-body font-medium text-apple-dark">{data.due_accounts.toLocaleString()}개</dd></div>}
          <div><dt className="text-caption text-apple-light">개인정보 처리 대기</dt><dd className="mt-1 text-body font-medium text-apple-dark">{pending.toLocaleString()}개</dd></div>
          <div><dt className="text-caption text-apple-light">계정 연결 확인 필요</dt><dd className="mt-1 text-body font-medium text-apple-dark">{data.coverage.unmapped_personal_fields.toLocaleString()}개 항목</dd></div>
          <div><dt className="text-caption text-apple-light">마지막 보고 성공 · KST</dt><dd className="mt-1 break-words text-body text-apple-dark">{displayTime(data.last_success_at)}</dd></div>
          <div><dt className="text-caption text-apple-light">다음 재시도 · KST</dt><dd className="mt-1 break-words text-body text-apple-dark">{displayTime(data.next_attempt_at, '예정 없음')}</dd></div>
        </dl>
      )}
      {data?.last_error && <p className="mb-4 text-body text-red-500" role="alert">최근 개인정보 보고에 실패했습니다. 연결 상태와 서버 운영 기록을 확인해 주세요.</p>}
      {data?.reporting_ready === false && <p className="mb-4 text-body text-apple-mid">연결, 개인정보 계정 연결 상태 및 대기 중인 정기 보고 처리가 필요합니다.</p>}
      {connect.isError && <p className="mb-4 text-body text-red-500" role="alert">승인 화면에 연결하지 못했습니다. 관리자 세션과 서버 연동 설정을 확인해 주세요.</p>}
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => connect.mutate()}
          disabled={connect.isPending || status.isPending}
          className="rounded-xl bg-brand-600 px-5 py-3 text-control font-medium text-white transition-colors hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {connect.isPending ? '승인 화면으로 이동 중...' : '개인정보 보고 연결'}
        </button>
        <button type="button" onClick={() => status.refetch()} disabled={status.isFetching} className="rounded-xl border border-apple-divider px-5 py-3 text-control text-apple-dark hover:bg-apple-gray disabled:opacity-40">상태 새로고침</button>
      </div>
    </>
  )
}

export default function AdminJiraPrivacyPage() {
  const { accessToken, isRestoring } = useAuthSession()
  const me = useMe()

  if (isRestoring || (accessToken && me.isLoading)) return <LoadingSpinner text="관리자 권한 확인 중..." />
  if (!accessToken) return <Navigate to="/admin" replace />

  const authorized = !me.isError && me.data?.login_required === true && me.data.is_superadmin === true

  return (
    <main className="min-h-screen bg-apple-bg px-4 py-8 sm:py-12">
      <div className="mx-auto w-full max-w-3xl rounded-2xl border border-apple-divider bg-apple-surface p-6 sm:p-8">
        <BrandLogo className="mb-6 w-56 max-w-full" />
        <h1 className="mb-6 text-page-title font-semibold text-apple-dark">{authorized ? 'Jira 개인정보 보고 연결' : '접근 권한이 없습니다'}</h1>
        {authorized ? <PrivacyConnection accessToken={accessToken} /> : <p className="text-body text-apple-mid">이 페이지는 최고 관리자 계정만 이용할 수 있습니다.</p>}
        <Link to="/" className="mt-8 inline-block text-control text-brand-600 hover:underline">대시보드로 돌아가기</Link>
      </div>
    </main>
  )
}
