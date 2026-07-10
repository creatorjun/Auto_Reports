// frontend/src/presentation/pages/LoginPage.tsx
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useLogin } from '@/infrastructure/hooks/useAuth'
import { useAuthStore } from '@/app/store/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { mutate: login, isPending, isError } = useLogin()
  const { accessToken } = useAuthStore()

  if (accessToken) return <Navigate to="/" replace />

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    login({ username, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-apple-bg">
      <div className="bg-white rounded-2xl shadow-sm border border-apple-divider/60 p-8 w-full max-w-sm">
        <div className="flex flex-col items-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1.2" fill="white" />
              <rect x="8" y="1" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="1" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.7" />
              <rect x="8" y="8" width="5" height="5" rx="1.2" fill="white" opacity="0.4" />
            </svg>
          </div>
          <h1 className="text-[18px] font-bold text-apple-dark tracking-tight">TAC \ubcf4\uace0\uc11c</h1>
          <p className="text-[12px] text-apple-light">\ub85c\uadf8\uc778\uc774 \ud544\uc694\ud569\ub2c8\ub2e4</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="\uc544\uc774\ub514"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-[13px]
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />
          <input
            type="password"
            placeholder="\ube44\ubc00\ubc88\ud638"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full px-4 py-2.5 rounded-xl border border-apple-divider text-[13px]
                       focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
                       placeholder:text-apple-light/60 text-apple-dark"
          />

          {isError && (
            <p className="text-[12px] text-red-500 text-center">\uc544\uc774\ub514 \ub610\ub294 \ube44\ubc00\ubc88\ud638\ub97c \ud655\uc778\ud558\uc138\uc694.</p>
          )}

          <button
            type="submit"
            disabled={isPending || !username || !password}
            className="mt-1 w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700
                       text-white text-[13px] font-medium transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPending ? '\ub85c\uadf8\uc778 \uc911...' : '\ub85c\uadf8\uc778'}
          </button>
        </form>
      </div>
    </div>
  )
}
