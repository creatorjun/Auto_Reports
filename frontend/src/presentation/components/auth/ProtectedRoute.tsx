// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useMe } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'
import { authApi } from '@/infrastructure/api/authApi'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, setAuth, setLoginRequired, clearAuth, username } = useAuthStore()
  const [refreshDone, setRefreshDone] = useState(false)

  useEffect(() => {
    if (accessToken) {
      setRefreshDone(true)
      return
    }
    authApi.refresh()
      .then((res) => {
        setAuth(res.access_token, username ?? '')
      })
      .catch(() => {
        clearAuth()
      })
      .finally(() => {
        setRefreshDone(true)
      })
  }, [])

  const { data, isLoading, isError } = useMe({ enabled: !!accessToken })

  useEffect(() => {
    if (data) setLoginRequired(data.login_required)
  }, [data, setLoginRequired])

  useEffect(() => {
    if (isError) clearAuth()
  }, [isError, clearAuth])

  if (!refreshDone) return <LoadingSpinner />

  if (!accessToken) return <Navigate to="/login" replace />

  if (isLoading) return <LoadingSpinner />

  if (isError) return <Navigate to="/login" replace />

  return <>{children}</>
}
