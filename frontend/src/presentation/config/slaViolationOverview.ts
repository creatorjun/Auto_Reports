// frontend/src/presentation/config/slaViolationOverview.ts
import type { SlaViolationScope } from '@/domain/SlaViolationOverview'

export const SLA_OVERVIEW_SCOPES: { key: SlaViolationScope; label: string; tone: string }[] = [
  { key: 'all', label: '전체 위반 티켓', tone: 'bg-brand-50 text-brand-600' },
  { key: 'initial_response', label: '최초응답 위반', tone: 'bg-amber-50 text-amber-700' },
  { key: 'resolution', label: '해결 위반', tone: 'bg-red-50 text-red-700' },
  { key: 'both', label: '동시 위반', tone: 'bg-purple-100 text-purple-700' },
]
