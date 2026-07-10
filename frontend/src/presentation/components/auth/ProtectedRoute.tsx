// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom'
import { useMe } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { data, isLoading, isError } = useMe()
  const { setLoginRequired, accessToken } = useAuthStore()

  if (isLoading) return <LoadingSpinner />

  if (isError) return <Navigate to="/login" replace />

  if (data) {
    setLoginRequired(data.login_required)
    if (data.login_required && !accessToken) {
      return <Navigate to="/login" replace />
    }
  }

  return <>{children}</>
}
