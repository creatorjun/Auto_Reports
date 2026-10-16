// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useMe } from '@/presentation/hooks/useAuth'
import { useAuthStore } from '@/presentation/state/authStore'
import { useAuthSession } from '@/presentation/hooks/useAuthSession'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, loginRequired, isRestoring } = useAuthSession()
  const { setLoginRequired, clearAuth } = useAuthStore()

  const { data, isLoading, isError } = useMe()

  useEffect(() => {
    if (data) setLoginRequired(data.login_required)
  }, [data, setLoginRequired])

  useEffect(() => {
    if (isError) clearAuth()
  }, [isError, clearAuth])

  if (isRestoring) return <LoadingSpinner />

  if (!loginRequired) return <>{children}</>

  if (!accessToken) return <Navigate to="/login" replace />

  if (isLoading) return <LoadingSpinner />

  if (isError) return <Navigate to="/login" replace />

  return <>{children}</>
}
