// frontend/src/presentation/components/security/SecurityNewsCard.tsx
import { ExternalLink, ShieldAlert } from 'lucide-react'
import type { SecurityNewsItem, SecurityNewsLanguage, SecuritySeverity } from '@/domain/SecurityNews'
import { cveReferenceUrl, safeSecurityNewsUrl, securityNewsDisplayText } from '@/application/services/securityNews'

export const securitySeverityLabels: Record<SecuritySeverity, string> = { critical: '치명적', high: '높음', medium: '보통', low: '낮음', unknown: '미평가' }
const severityClasses: Record<SecuritySeverity, string> = { critical: 'badge-critical', high: 'badge-warning', medium: 'badge-neutral', low: 'badge-good', unknown: 'badge-neutral' }
const kindLabels = { cve: 'CVE 취약점', advisory: '보안 권고', news: '보안 뉴스' }

export function securityDateLabel(value: string | null, includeTime = false): string {
  if (!value || !Number.isFinite(Date.parse(value))) return '날짜 미제공'
  return new Date(value).toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(includeTime ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
  })
}

export default function SecurityNewsCard({ item, sourceName, language = 'ko' }: { item: SecurityNewsItem; sourceName: string; language?: SecurityNewsLanguage }) {
  const url = safeSecurityNewsUrl(item.url)
  const isKev = item.source_id.toLowerCase().includes('kev')
  const display = securityNewsDisplayText(item, language)
  return (
    <article className={`flex min-w-0 flex-col rounded-2xl border bg-apple-surface p-5 shadow-apple-sm transition-shadow hover:shadow-apple md:p-6 ${item.known_exploited ? 'border-red-200' : 'border-apple-divider/70'}`}>
      <div className="flex flex-wrap items-center gap-2 text-caption">
        <span className="font-semibold text-brand-600">{sourceName}</span>
        <span className="text-apple-light" aria-hidden="true">·</span>
        <span className="text-apple-mid">{kindLabels[item.kind]}</span>
        {display.translated && <span className="rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-caption text-brand-700">AI 번역</span>}
        {display.originalFallback && <span className="badge-neutral">{display.translated ? '일부 원문 표시' : '원문 표시'}</span>}
        {item.known_exploited && <span className="badge-critical gap-1"><ShieldAlert size={12} aria-hidden="true" />실제 악용 확인</span>}
      </div>
      <h2 className="mt-3 break-words text-section-title font-semibold leading-snug tracking-tight text-apple-dark">
        {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="rounded hover:text-brand-600 focus-visible:outline-brand-500">{display.title}</a> : display.title}
      </h2>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {item.kind !== 'news' && <span className={severityClasses[item.severity]}>{securitySeverityLabels[item.severity]}{item.cvss_score !== null ? ` · CVSS ${item.cvss_score.toFixed(1)}` : ''}{item.cvss_version ? ` (v${item.cvss_version})` : ''}</span>}
        {item.cve_ids.slice(0, 6).map((id) => {
          const href = cveReferenceUrl(id)
          return href ? <a key={id} href={href} target="_blank" rel="noopener noreferrer" className="rounded-md border border-apple-divider bg-apple-gray px-2 py-0.5 text-caption font-medium text-apple-mid hover:text-brand-600 focus-visible:outline-brand-500" aria-label={`${id} NVD 상세`}>{id}</a> : null
        })}
        {item.cve_ids.length > 6 && <span className="text-caption text-apple-light">외 {item.cve_ids.length - 6}개</span>}
      </div>
      {display.summary && <p className="mt-3 line-clamp-4 break-words text-label leading-relaxed text-apple-mid">{display.summary}</p>}
      {(item.vendor || item.product) && <p className="mt-3 break-words text-caption text-apple-mid"><span className="font-medium text-apple-dark">관련 제품</span> · {[item.vendor, item.product].filter(Boolean).join(' / ')}</p>}
      {isKev && item.due_date && <p className="mt-2 text-caption text-apple-mid">미 연방기관 조치 기한 · {securityDateLabel(item.due_date)}</p>}
      <div className="mt-auto flex flex-wrap items-end justify-between gap-3 pt-5 text-caption">
        <div className="space-y-1 text-apple-light">
          <p>{isKev ? 'KEV 등록' : item.published_at ? '게시' : '수정'} · {securityDateLabel(item.published_at ?? item.updated_at)}</p>
          {item.updated_at && item.published_at && item.updated_at !== item.published_at && <p>수정 · {securityDateLabel(item.updated_at)}</p>}
        </div>
        {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 font-semibold text-brand-600 hover:bg-brand-50 focus-visible:outline-brand-500" aria-label={`${display.title} 원문 보기 (새 창)`}>원문 보기<ExternalLink size={13} aria-hidden="true" /></a> : <span className="text-apple-light">원문 링크 없음</span>}
      </div>
    </article>
  )
}
