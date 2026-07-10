// frontend/src/presentation/pages/LoginPage.tsx
import { useState } from 'react'
import { useLogin } from '@/infrastructure/hooks/useAuth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { mutate: login, isPending, error } = useLogin()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return
    login({ username: username.trim(), password })
  }

  const isError = !!error

  return (
    <div className="min-h-screen bg-apple-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto mb-4 shadow-lg">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round" />
              <path d="M12 22V12M2 7l10 5 10-5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="text-[22px] font-semibold text-apple-dark tracking-tight">TAC Auto Reports</h1>
          <p className="text-[13px] text-apple-light mt-1">로그인이 필요합니다</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          <div className="space-y-1">
            <label className="text-[12px] font-medium text-apple-light">아이디</label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              className={`w-full px-3.5 py-2.5 rounded-xl text-[14px] border transition-colors
                bg-white text-apple-dark placeholder:text-apple-light/50
                focus:outline-none focus:ring-2 focus:ring-brand-400/50
                ${isError ? 'border-red-300' : 'border-apple-divider'}`}
            />
          </div>

          <div className="space-y-1">
            <label className="text-[12px] font-medium text-apple-light">비밀번호</label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className={`w-full px-3.5 py-2.5 rounded-xl text-[14px] border transition-colors
                bg-white text-apple-dark placeholder:text-apple-light/50
                focus:outline-none focus:ring-2 focus:ring-brand-400/50
                ${isError ? 'border-red-300' : 'border-apple-divider'}`}
            />
          </div>

          {isError && (
            <p className="text-[12px] text-red-500">
              아이디 또는 비밀번호가 올바르지 않습니다.
            </p>
          )}

          <button
            type="submit"
            disabled={isPending || !username.trim() || !password}
            className="w-full py-2.5 rounded-xl text-[14px] font-semibold
                       bg-brand-600 hover:bg-brand-700 text-white
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isPending && (
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
              </svg>
            )}
            {isPending ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </div>
  )
}
