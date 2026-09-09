// frontend/src/domain/DashboardStatusPolicy.ts
const DASHBOARD_STATUS_ORDER = [
  '할 일',
  '재오픈',
  '자료 요청 중',
  '이슈 리뷰 중',
  '연구소 대기 중',
  '연구소 검토 중',
  '구현 중',
  '처리 중',
  '배포 파일 검토 중',
  '결과 대기 중',
  '보류 중',
  '영업본부 검토중',
  'Closed',
  '닫혀',
  '닫힘',
  '반려됨',
  '중복 이슈',
  '취소됨',
] as const

const STATUS_ORDER_INDEX: ReadonlyMap<string, number> = new Map(
  DASHBOARD_STATUS_ORDER.map((status, index) => [status, index]),
)

export function isDashboardStatusIncluded(
  status: string,
  selectedStatuses: ReadonlySet<string> | null,
): boolean {
  return selectedStatuses === null || selectedStatuses.has(status)
}

export function sortDashboardStatuses(statuses: Iterable<string>): string[] {
  return [...new Set(statuses)].sort((left, right) => (
    (STATUS_ORDER_INDEX.get(left) ?? Number.MAX_SAFE_INTEGER)
    - (STATUS_ORDER_INDEX.get(right) ?? Number.MAX_SAFE_INTEGER)
    || left.localeCompare(right, 'ko-KR', { numeric: true, sensitivity: 'base' })
  ))
}
