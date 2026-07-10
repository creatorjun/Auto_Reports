// frontend/src/infrastructure/hooks/useAuth.ts
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/infrastructure/api/authApi'
import { useAuthStore } from '@/app/store/authStore'

export const useMe = () =>
  useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authApi.me,
    retry: false,
    staleTime: 1000 * 60 * 5,
  })

export const useLogin = () => {
  const { setAuth, setLoginRequired } = useAuthStore()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.login(username, password),
    onSuccess: async (data) => {
      const me = await authApi.me()
      setLoginRequired(me.login_required)
      setAuth(data.access_token, me.username)
      navigate('/')
    },
  })
}

export const useLogout = () => {
  const { clearAuth } = useAuthStore()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearAuth()
      navigate('/login')
    },
  })
}
