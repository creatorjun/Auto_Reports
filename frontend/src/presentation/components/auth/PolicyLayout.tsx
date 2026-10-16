// frontend/src/presentation/components/auth/PolicyLayout.tsx
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import BrandLogo from '@/presentation/components/common/BrandLogo'

export const POLICY_SUPPORT_EMAIL = 'jh.han@seculayer.com'

export function PolicySection({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="space-y-3">
      <h2 id={id} className="text-section-title font-semibold text-apple-dark">{title}</h2>
      <div className="space-y-3 text-body leading-relaxed text-apple-mid">{children}</div>
    </section>
  )
}

export function PolicySupportLink() {
  return <a className="break-all text-brand-600 underline underline-offset-4" href={`mailto:${POLICY_SUPPORT_EMAIL}`}>{POLICY_SUPPORT_EMAIL}</a>
}

export default function PolicyLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="min-h-screen bg-apple-bg px-4 py-6 sm:px-6 sm:py-10">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-5">
          <BrandLogo className="w-52 max-w-full" />
          <Link to="/login" className="rounded-xl border border-apple-divider bg-apple-surface px-4 py-2 text-control text-apple-dark transition-colors hover:bg-apple-gray">로그인으로 돌아가기</Link>
        </header>
        <article className="min-w-0 space-y-8 rounded-2xl border border-apple-divider/60 bg-apple-surface p-5 shadow-sm sm:p-8">
          <div className="space-y-3 border-b border-apple-divider pb-6">
            <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">{title}</h1>
            <p className="text-caption text-apple-light">운영: SecuLayer · 시행일: 2026년 10월 16일</p>
          </div>
          {children}
        </article>
        <footer className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3 py-6 text-caption text-apple-mid">
          <Link to="/privacy" className="hover:text-brand-600">개인정보처리방침</Link>
          <Link to="/terms" className="hover:text-brand-600">이용약관</Link>
          <PolicySupportLink />
        </footer>
      </div>
    </main>
  )
}
