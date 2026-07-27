// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useMe } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, setLoginRequired, clearAuth } = useAuthStore()
  const { data, isLoading, isError } = useMe()

  useEffect(() => {
    if (data) setLoginRequired(data.login_required)
  }, [data, setLoginRequired])

  useEffect(() => {
    if (isError) clearAuth()
  }, [isError, clearAuth])

  if (!accessToken) return <Navigate to="/login" replace />

  if (isLoading) return <LoadingSpinner />

  if (isError) return <Navigate to="/login" replace />

  return <>{children}</>
}
