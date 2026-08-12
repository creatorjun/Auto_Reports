// frontend/src/presentation/components/auth/ProtectedRoute.tsx
import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useMe } from '@/presentation/hooks/useAuth'
import { useAuthStore } from '@/presentation/state/authStore'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { auth } = useApplicationServices()
  const { accessToken, setAuth, setLoginRequired, clearAuth, username } = useAuthStore()
  const [refreshDone, setRefreshDone] = useState(false)

  useEffect(() => {
    if (accessToken) {
      setRefreshDone(true)
      return
    }
    auth.refresh()
      .then((res) => {
        setAuth(res.access_token, username ?? '')
      })
      .catch(() => {
        clearAuth()
      })
      .finally(() => {
        setRefreshDone(true)
      })
  }, [accessToken, auth, clearAuth, setAuth, username])

  const { data, isLoading, isError } = useMe()

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
