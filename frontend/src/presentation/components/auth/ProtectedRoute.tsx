// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMe } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { data, isLoading, isError } = useMe()
  const { setLoginRequired } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (data) setLoginRequired(data.login_required)
    if (!isLoading && isError) navigate('/login', { replace: true })
  }, [data, isLoading, isError, navigate, setLoginRequired])

  if (isLoading) return <LoadingSpinner />
  if (isError) return null

  return <>{children}</>
}
