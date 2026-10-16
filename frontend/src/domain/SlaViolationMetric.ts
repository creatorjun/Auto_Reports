// frontend/src/domain/SlaViolationMetric.ts
import type { SlaViolationTicket } from './SlaViolationReport'

export const SLA_VIOLATION_METRICS = [
  { key: 'initial_response', label: '최초응답 위반' },
  { key: 'resolution', label: '해결시간 위반' },
] as const

export function slaViolatedMetrics(ticket: SlaViolationTicket) {
  return SLA_VIOLATION_METRICS.filter(({ key }) => ticket.breaches.some((breach) => breach.metric === key))
}

export function slaViolationLabel(ticket: SlaViolationTicket): string {
  return slaViolatedMetrics(ticket).map(({ label }) => label).join(' · ') || '확인 불가'
}
