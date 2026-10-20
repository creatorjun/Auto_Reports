// frontend/src/presentation/components/security/SecurityNewsTranslationControls.tsx
import { Languages, LoaderCircle } from 'lucide-react'
import type { SecurityNewsLanguage, SecurityNewsTranslation } from '@/domain/SecurityNews'

export default function SecurityNewsTranslationControls({ language, onLanguageChange, translation }: {
  language: SecurityNewsLanguage
  onLanguageChange: (language: SecurityNewsLanguage) => void
  translation?: SecurityNewsTranslation
}) {
  const heading = translation?.translating
    ? '한국어 번역 중'
    : translation?.pending_count
      ? translation.message ? '한국어 번역 일시 대기' : '한국어 번역 대기'
      : translation?.translated_count ? '한국어 번역 완료' : '표시 언어'
  return (
    <section aria-label="보안 정보 표시 언어" className="flex min-w-0 flex-col justify-between gap-3 rounded-2xl border border-apple-divider/70 bg-apple-surface px-4 py-4 sm:flex-row sm:items-center md:px-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-control">
          {translation?.translating ? <LoaderCircle size={16} aria-hidden="true" className="animate-spin text-brand-600" /> : <Languages size={16} aria-hidden="true" className="text-brand-600" />}
          <p role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-semibold text-apple-dark">{heading}</span>
            {translation && <span className="text-caption tabular-nums text-apple-mid">번역 완료 {translation.translated_count.toLocaleString('ko-KR')}건 · 대기 {translation.pending_count.toLocaleString('ko-KR')}건</span>}
          </p>
        </div>
        <p className="mt-2 break-words text-caption leading-relaxed text-apple-mid">{translation?.message || (translation?.translating ? '번역이 준비되는 대로 자동으로 반영합니다. 기다리는 항목은 원문으로 표시합니다.' : '한국어 번역이 없는 항목은 원문으로 표시합니다.')}</p>
      </div>
      <div role="group" aria-label="표시 언어 선택" className="inline-flex shrink-0 self-start gap-1 rounded-xl bg-apple-gray p-1 sm:self-center">
        {[{ value: 'ko', label: '한국어' }, { value: 'original', label: '원문' }].map((choice) => <button key={choice.value} type="button" aria-pressed={language === choice.value} onClick={() => onLanguageChange(choice.value as SecurityNewsLanguage)}
          className={`rounded-lg px-4 py-2 text-control font-semibold transition-colors focus-visible:outline-brand-500 ${language === choice.value ? 'bg-apple-surface text-brand-600 shadow-apple-sm' : 'text-apple-mid hover:text-apple-dark'}`}>{choice.label}</button>)}
      </div>
    </section>
  )
}
