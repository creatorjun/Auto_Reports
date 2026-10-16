// frontend/src/presentation/utils/slaViolationFormatters.ts
const timestampFormatter = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const dateFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' })

export function slaTimestamp(value: string | null): string {
  const date = value ? new Date(value) : null
  return date && Number.isFinite(date.getTime()) ? timestampFormatter.format(date) : '확인 불가'
}

export function slaCreatedDate(value: string): string {
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '확인 불가'
  const parts = Object.fromEntries(dateFormatter.formatToParts(date).map((part) => [part.type, part.value]))
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function slaDuration(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value < 0) return '확인 불가'
  if (value === 0) return '0분'
  if (value < 60_000) return '1분 미만'
  const minutes = Math.floor(value / 60_000)
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return [hours ? `${hours.toLocaleString('ko-KR')}시간` : '', remainder ? `${remainder}분` : ''].filter(Boolean).join(' ')
}
