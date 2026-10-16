// frontend/src/presentation/hooks/useAuthSession.ts
import { useEffect } from 'react'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

export function useAuthSession() {
  const { auth } = useApplicationServices()
  const { accessToken, loginRequired, sessionReady, username, setAuth, setLoginRequired, clearAuth } = useAuthStore()

  useEffect(() => {
    if (sessionReady) return
    let active = true
    auth.refresh()
      .then((data) => {
        if (active && !useAuthStore.getState().sessionReady) {
          setAuth(data.access_token, data.display_name ?? data.username ?? username ?? '')
          setLoginRequired(true)
        }
      })
      .catch(async () => {
        if (!active || useAuthStore.getState().sessionReady) return
        try {
          const data = await auth.me()
          if (!active || useAuthStore.getState().sessionReady) return
          if (!data.login_required) setLoginRequired(false)
          else clearAuth()
        } catch {
          if (active && !useAuthStore.getState().sessionReady) clearAuth()
        }
      })
    return () => { active = false }
  }, [auth, clearAuth, sessionReady, setAuth, setLoginRequired, username])

  return { accessToken, loginRequired, isRestoring: !sessionReady }
}
