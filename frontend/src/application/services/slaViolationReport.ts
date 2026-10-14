// frontend/src/application/services/slaViolationReport.ts
import type { SlaViolationMetric, SlaViolationPeriod, SlaViolationTicket } from '@/domain/SlaViolationReport'

export const SLA_PERIOD_LABELS: Record<SlaViolationPeriod, string> = { week: '주간', month: '월간', year: '연간' }
export const SLA_METRIC_LABELS: Record<SlaViolationMetric, string> = { initial_response: '최초응답 위반', resolution: '해결 위반' }

export function slaToday(now = new Date()): string {
  return new Date(now.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10)
}

export function slaDateRange(period: SlaViolationPeriod, selectedDate: string): { start: string; end: string } | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(selectedDate)) return null
  const start = new Date(`${selectedDate}T00:00:00Z`)
  if (!Number.isFinite(start.getTime()) || start.toISOString().slice(0, 10) !== selectedDate || start.getUTCFullYear() < 1) return null
  const end = new Date(start)
  if (period === 'week') {
    start.setUTCDate(start.getUTCDate() - (start.getUTCDay() + 6) % 7)
    end.setTime(start.getTime())
    end.setUTCDate(end.getUTCDate() + 6)
  } else if (period === 'month') {
    start.setUTCDate(1)
    end.setUTCMonth(end.getUTCMonth() + 1, 0)
  } else {
    start.setUTCMonth(0, 1)
    end.setUTCMonth(11, 31)
  }
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) }
}

export function slaTicketsForMetric(tickets: SlaViolationTicket[], metric: SlaViolationMetric): SlaViolationTicket[] {
  return tickets.filter((ticket) => ticket.breaches.some((breach) => breach.metric === metric))
}

export function slaPartnersLabel(partners: string[] | null): string {
  return partners === null ? '확인 불가' : partners.length ? partners.join(', ') : '본사'
}
