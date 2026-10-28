// frontend/src/application/services/cveInventory.ts
import type { CveCollectionStatus, CveInventoryImpact, CveInventoryRequest } from '@/domain/CveInventory'

export function defaultCveInventoryRequest(): CveInventoryRequest {
  return { severity: 'all', search: '', ecosystem: 'all', impact: 'all', page: 1, page_size: 50, sort: 'severity' }
}

export const cveImpactLabels: Record<CveInventoryImpact, string> = {
  affected: '영향받음', not_affected: '영향받지 않음', unknown: '확인 필요',
}

export const cveCollectionLabels: Record<CveCollectionStatus, string> = {
  ok: '조회 완료', stale: '이전 자료', error: '조회 실패', pending: '조회 대기', unmapped: '매핑 필요',
}

export function cvePageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / Math.max(1, pageSize)))
}

export function cveSafeReferences(references: readonly string[]): string[] {
  const result = new Set<string>()
  for (const value of references) {
    try {
      const url = new URL(value)
      if ((url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password) result.add(url.href)
    } catch {}
  }
  return [...result]
}
