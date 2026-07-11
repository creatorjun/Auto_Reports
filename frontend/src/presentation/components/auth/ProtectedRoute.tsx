// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useMe } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { data, isLoading, isError } = useMe()
  const { setLoginRequired, accessToken } = useAuthStore()

  useEffect(() => {
    if (data) setLoginRequired(data.login_required)
  }, [data, setLoginRequired])

  if (isLoading) return <LoadingSpinner />

  if (isError) return <Navigate to="/login" replace />

  if (data === undefined) return <Navigate to="/login" replace />

  if (data.login_required && !accessToken) return <Navigate to="/login" replace />

  return <>{children}</>
}
