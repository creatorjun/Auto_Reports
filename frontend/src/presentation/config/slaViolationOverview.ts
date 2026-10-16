// frontend/src/presentation/config/slaViolationOverview.ts
import type { SlaViolationScope } from '@/domain/SlaViolationOverview'

export const SLA_OVERVIEW_SCOPES: {
  key: SlaViolationScope
  label: string
  tone: string
  valueTone: string
  selectionRing: string
  hoverRing: string
}[] = [
  { key: 'all', label: '전체 위반 티켓', tone: 'bg-blue-50 text-blue-500', valueTone: 'text-blue-600', selectionRing: 'ring-blue-200', hoverRing: 'hover:ring-blue-200' },
  { key: 'initial_response', label: '최초응답 위반', tone: 'bg-amber-50 text-amber-500', valueTone: 'text-amber-600', selectionRing: 'ring-amber-200', hoverRing: 'hover:ring-amber-200' },
  { key: 'resolution', label: '해결 위반', tone: 'bg-red-50 text-red-500', valueTone: 'text-red-600', selectionRing: 'ring-red-200', hoverRing: 'hover:ring-red-200' },
  { key: 'both', label: '동시 위반', tone: 'bg-purple-100 text-purple-700', valueTone: 'text-purple-700', selectionRing: 'ring-purple-200', hoverRing: 'hover:ring-purple-200' },
]
