// frontend/src/infrastructure/hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi, type LoginRequest } from '@/infrastructure/api/authApi'
import { useAuthStore } from '@/app/store/authStore'

export const useMe = () => {
  const { accessToken } = useAuthStore()
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    enabled: !!accessToken,
    retry: false,
    staleTime: 5 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    throwOnError: false,
    meta: {
      onError: () => {
        queryClient.removeQueries({ queryKey: ['me'] })
      },
    },
  })
}

export const useLogin = () => {
  const queryClient = useQueryClient()
  const { setAuth, setLoginRequired } = useAuthStore()
  return useMutation<ReturnType<typeof authApi.login> extends Promise<infer T> ? T : never, Error, LoginRequest>({
    mutationFn: authApi.login,
    onSuccess: (data, variables) => {
      setAuth(data.access_token, variables.username)
      setLoginRequired(true)
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export const useLogout = () => {
  const queryClient = useQueryClient()
  const { clearAuth } = useAuthStore()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: authApi.logout,
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
