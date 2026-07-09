// frontend/src/presentation/components/common/StatusBadge.tsx
const CLOSED = new Set([
  'Closed', '중복 이슈', '반려됨', '취소됨', '닫힘',
])

const ACTIVE = new Set([
  '할 일', '재오픈', '이슈 리뷰 중',
  '연구소 대기 중', '연구소 검토 중', '구현 중',
  '배포 파일 검토 중', '자료 요청 중', '결과 대기 중',
  '보류 중', '영업본부 검토중',
])

export function StatusBadge({ status }: { status: string }) {
  if (CLOSED.has(status)) return <span className="badge-good">{status}</span>
  if (ACTIVE.has(status)) return <span className="badge-warning">{status}</span>
  return <span className="badge-neutral">{status}</span>
}
