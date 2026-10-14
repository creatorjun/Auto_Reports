// frontend/src/application/services/slaViolationReport.ts
import type { SlaViolationMetric, SlaViolationTicket } from '@/domain/SlaViolationReport'

export { REPORT_PERIOD_LABELS as SLA_PERIOD_LABELS, reportToday as slaToday, reportDateRange as slaDateRange } from '@/application/services/reportPeriod'
export const SLA_METRIC_LABELS: Record<SlaViolationMetric, string> = { initial_response: '최초응답 위반', resolution: '해결 위반' }

export function slaTicketsForMetric(tickets: SlaViolationTicket[], metric: SlaViolationMetric): SlaViolationTicket[] {
  return tickets.filter((ticket) => ticket.breaches.some((breach) => breach.metric === metric))
}

export function slaPartnersLabel(partners: string[] | null): string {
  return partners === null ? '확인 불가' : partners.length ? partners.join(', ') : '본사'
}

export function slaVisibleStatusDurations(durations: SlaViolationTicket['status_durations']): SlaViolationTicket['status_durations'] {
  return durations?.filter(({ status }) => !['닫힘', '닫혀', 'closed'].includes(status.normalize('NFKC').trim().toLowerCase())) ?? null
}
