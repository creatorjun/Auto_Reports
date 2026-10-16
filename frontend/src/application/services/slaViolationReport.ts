// frontend/src/application/services/slaViolationReport.ts
import type { SlaViolationTicket } from '@/domain/SlaViolationReport'

export { REPORT_PERIOD_LABELS as SLA_PERIOD_LABELS, reportToday as slaToday, reportDateRange as slaDateRange } from '@/application/services/reportPeriod'
export function slaPartnersLabel(partners: string[] | null): string {
  return partners === null ? '확인 불가' : partners.length ? partners.join(', ') : '본사'
}

export function slaVisibleStatusDurations(durations: SlaViolationTicket['status_durations']): SlaViolationTicket['status_durations'] {
  return durations?.filter(({ status }) => !['닫힘', '닫혀', 'closed', '결과대기중', '자료요청중'].includes(status.normalize('NFKC').replace(/\s+/g, '').toLowerCase())) ?? null
}
