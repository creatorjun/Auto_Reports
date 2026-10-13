// frontend/src/presentation/components/clevel/CLevelShared.tsx
import type { CSSProperties } from 'react'
import { RequestError } from '@/application/errors/RequestError'
import { CLEVEL_OWNER_COLORS, CLEVEL_TYPES, cLevelNumber, cLevelText } from '@/application/services/cLevelReport'
import type { CLevelOwner } from '@/domain/CLevelReport'

export function CLevelTypeLabel({ type, label }: { type: string; label?: string }) {
  const definition = CLEVEL_TYPES.find((entry) => entry.type === type)
  return <span className="cl-type"><i style={{ background: definition?.color ?? 'currentColor' }} />{label ?? definition?.label ?? '전체'}</span>
}

export function CLevelStatus({ status }: { status: string | null | undefined }) {
  const colors: Record<string, string> = { '이슈 리뷰 중': '#c49b3b', '자료 요청 중': '#439cb8', '연구소 대기 중': '#9a75b6', '연구소 검토 중': '#9a75b6', '구현 중': '#88a84b', '처리 중': '#88a84b', '배포 파일 검토 중': '#459f9c', '결과 대기 중': '#ca7474' }
  const color = status ? colors[status] : undefined
  return <span className="cl-status" style={color ? { color, background: `${color}20` } : undefined}>{cLevelText(status)}</span>
}

export function CLevelOwnerDot({ owner }: { owner: CLevelOwner }) {
  return <span className="cl-owner-label"><i style={{ background: CLEVEL_OWNER_COLORS[owner] }} />{owner}</span>
}

export function CLevelNumber({ value, unit = '', digits = 0 }: { value: number | null | undefined; unit?: string; digits?: number }) {
  return <span className={value == null ? 'cl-unknown' : 'cl-number'}>{cLevelNumber(value, unit, digits)}</span>
}

export function CLevelDelta({ value }: { value: number | null | undefined }) {
  return <span className={`cl-delta ${value != null && value > 0 ? 'is-up' : value != null && value < 0 ? 'is-down' : ''}`}>{value == null ? '확인 불가' : `${value > 0 ? '+' : ''}${cLevelNumber(value)}`}</span>
}

export function cLevelError(error: unknown): string {
  if (error instanceof RequestError && typeof error.detail === 'string') return error.detail
  return error instanceof Error && !(error instanceof RequestError) ? error.message : '요청을 처리하지 못했습니다. 다시 시도해 주세요.'
}

export function cLevelWidth(value: number, total: number): CSSProperties {
  return { width: `${total > 0 ? Math.max(0, Math.min(100, value / total * 100)) : 0}%` }
}
