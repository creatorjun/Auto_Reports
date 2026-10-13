// frontend/src/presentation/hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { LoginRequest } from '@/domain/Auth'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'

export const useMe = () => {
  const { auth } = useApplicationServices()
  const { accessToken } = useAuthStore()
  return useQuery({
    queryKey: ['me', accessToken],
    queryFn: auth.me,
    enabled: !!accessToken,
    retry: false,
    staleTime: 60 * 1000,
    gcTime: 0,
    refetchOnWindowFocus: false,
    throwOnError: false,
  })
}

export const useLogin = () => {
  const { auth } = useApplicationServices()
  const queryClient = useQueryClient()
  const { setAuth, setLoginRequired } = useAuthStore()
  return useMutation({
    mutationFn: (request: LoginRequest) => auth.login(request),
    onSuccess: (data, variables) => {
      queryClient.removeQueries({ queryKey: ['me'] })
      queryClient.removeQueries({ queryKey: ['audit-logs'] })
      setAuth(data.access_token, variables.username)
      setLoginRequired(true)
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export const useLogout = () => {
  const { auth } = useApplicationServices()
  const queryClient = useQueryClient()
  const { clearAuth } = useAuthStore()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: auth.logout,
    onSuccess: () => {
      clearAuth()
      queryClient.clear()
      navigate('/login', { replace: true })
    },
    onError: () => {
      clearAuth()
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })
}
