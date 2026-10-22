// frontend/src/presentation/components/security/securityNewsFormatting.ts
import type { SecuritySeverity } from '@/domain/SecurityNews'

export const securitySeverityLabels: Record<SecuritySeverity, string> = { critical: '치명적', high: '높음', medium: '보통', low: '낮음', unknown: '미평가' }
export const securitySeverityClasses: Record<SecuritySeverity, string> = { critical: 'badge-critical', high: 'badge-warning', medium: 'badge-neutral', low: 'badge-good', unknown: 'badge-neutral' }
const dateOptions: Intl.DateTimeFormatOptions = { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }
const dateFormatter = new Intl.DateTimeFormat('ko-KR', dateOptions)
const timestampFormatter = new Intl.DateTimeFormat('ko-KR', { ...dateOptions, hour: '2-digit', minute: '2-digit', hour12: false })

export function securityDateLabel(value: string | null, includeTime = false): string {
  const timestamp = value ? Date.parse(value) : NaN
  return Number.isFinite(timestamp) ? (includeTime ? timestampFormatter : dateFormatter).format(timestamp) : '날짜 미제공'
}
