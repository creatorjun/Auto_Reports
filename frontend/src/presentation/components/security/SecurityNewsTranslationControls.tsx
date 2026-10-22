// frontend/src/presentation/components/security/SecurityNewsTranslationControls.tsx
import { Languages, LoaderCircle } from 'lucide-react'
import type { SecurityNewsLanguage, SecurityNewsTranslation } from '@/domain/SecurityNews'

export default function SecurityNewsTranslationControls({ language, onLanguageChange, translation }: {
  language: SecurityNewsLanguage
  onLanguageChange: (language: SecurityNewsLanguage) => void
  translation?: SecurityNewsTranslation
}) {
  const status = translation?.translating
    ? 'AI 요약 중'
    : translation?.message ? 'AI 요약 일시 대기' : translation?.pending_count ? 'AI 요약 대기' : null
  return (
    <section aria-label="보안 정보 표시 언어" className="flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-2xl border border-apple-divider/70 bg-apple-surface px-4 py-2 md:px-5">
      <div className="flex min-w-0 flex-wrap items-center gap-2 text-control">
        {translation?.translating ? <LoaderCircle size={16} aria-hidden="true" className="animate-spin text-brand-600" /> : <Languages size={16} aria-hidden="true" className="text-brand-600" />}
        <span className="font-semibold text-apple-dark">목록 표시</span>
        {status && <span role="status" title={translation?.message || undefined} className={`text-caption ${translation?.message ? 'text-amber-700' : 'text-apple-mid'}`}>{status}{translation?.pending_count ? ` · ${translation.pending_count.toLocaleString('ko-KR')}건` : ''}</span>}
      </div>
      <div role="group" aria-label="표시 언어 선택" className="inline-flex shrink-0 gap-1 rounded-xl bg-apple-gray p-1">
        {[{ value: 'ko', label: '한 줄 요약' }, { value: 'original', label: '원문 제목' }].map((choice) => <button key={choice.value} type="button" aria-pressed={language === choice.value} onClick={() => onLanguageChange(choice.value as SecurityNewsLanguage)}
          className={`rounded-lg px-4 py-2 text-control font-semibold transition-colors focus-visible:outline-brand-500 ${language === choice.value ? 'bg-apple-surface text-brand-600 shadow-apple-sm' : 'text-apple-mid hover:text-apple-dark'}`}>{choice.label}</button>)}
      </div>
    </section>
  )
}
