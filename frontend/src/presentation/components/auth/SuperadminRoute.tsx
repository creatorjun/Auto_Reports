// frontend/src/presentation/components/auth/SuperadminRoute.tsx
import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { canViewAuditLogs } from '@/domain/Auth'
import { useMe } from '@/presentation/hooks/useAuth'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function SuperadminRoute({ children }: { children: React.ReactNode }) {
  const me = useMe()
  if (me.isLoading) return <LoadingSpinner text="관리자 권한 확인 중..." />
  if (!me.isError && canViewAuditLogs(me.data)) return <>{children}</>
  return (
    <div className="m-6 rounded-2xl border border-apple-divider bg-apple-surface p-8 text-center">
      <ShieldAlert className="mx-auto mb-4 text-apple-light" size={32} />
      <h1 className="text-lg font-semibold text-apple-dark">감사로그 접근 권한이 없습니다</h1>
      <p className="mt-2 text-sm text-apple-mid">관리자 계정으로 로그인하면 감사로그를 확인할 수 있습니다.</p>
      <Link className="mt-6 inline-block rounded-xl bg-apple-gray px-4 py-2 text-sm text-apple-dark" to="/">대시보드로 돌아가기</Link>
    </div>
  )
}
