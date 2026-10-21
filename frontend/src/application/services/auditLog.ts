// frontend/src/application/services/auditLog.ts
import type { AuditLogQuery } from '@/domain/AuditLog'

export interface AuditLogFilters {
  start_date: string
  end_date: string
  event: string
  username: string
  ip: string
  search: string
}

export function auditLogQuery(filters: AuditLogFilters, page: number, limit = 50): AuditLogQuery {
  const query: AuditLogQuery = { limit, offset: Math.max(0, page) * limit }
  for (const key of ['start_date', 'end_date', 'event', 'username', 'ip', 'search'] as const) {
    const value = filters[key].trim()
    if (value) query[key] = value
  }
  return query
}

export function auditFilterError(filters: AuditLogFilters): string | null {
  return filters.start_date && filters.end_date && filters.start_date > filters.end_date
    ? '시작일은 종료일보다 늦을 수 없습니다.' : null
}

export function auditDefaultFilters(now = new Date()): AuditLogFilters {
  const today = new Date(now.getTime() + 9 * 60 * 60 * 1000)
  const start = new Date(today)
  start.setUTCDate(start.getUTCDate() - 6)
  return { start_date: start.toISOString().slice(0, 10), end_date: today.toISOString().slice(0, 10), event: '', username: '', ip: '', search: '' }
}

const EVENT_LABELS: Record<string, string> = {
  LOGIN_SUCCESS: '로그인 성공', LOGIN_FAILED: '로그인 실패', LOGIN_FAIL: '로그인 실패',
  LOGOUT: '로그아웃', TOKEN_REFRESH: '세션 갱신', REFRESH_SUCCESS: '세션 갱신',
  REPORT_TRIGGER: '보고서 생성', REPORT_DELETE: '보고서 삭제',
  SLA_VIOLATION_REPORT_CREATE: 'SLA 위반 보고서 생성',
  FILE_UPLOAD: '파일 업로드', FILE_DELETE: '파일 삭제', FILE_MOVE: '파일 이동',
  FILE_DOWNLOAD: '파일 다운로드', FOLDER_CREATE: '폴더 생성', FOLDER_DELETE: '폴더 삭제',
  CHUNKED_INIT: '분할 업로드 시작', CHUNKED_COMPLETE: '분할 업로드 완료', CHUNKED_ABORT: '분할 업로드 취소',
  AUDIT_LOG_VIEW: '감사로그 조회',
}

export function auditEventLabel(event: string): string {
  return EVENT_LABELS[event] ?? event
}

export function visibleAuditDetails(details: Record<string, string>): [string, string][] {
  return Object.entries(details).filter(([key]) => !/(?:password|passwd|secret|token|authorization|cookie|credential|private.?key)/i.test(key))
}
