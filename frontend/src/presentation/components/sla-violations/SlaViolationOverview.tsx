// frontend/src/presentation/components/sla-violations/SlaViolationOverview.tsx
import { useMemo } from 'react'
import { AlarmClock, Clock3, Layers, ShieldAlert } from 'lucide-react'
import type { SlaViolationReport, SlaViolationTicket } from '@/domain/SlaViolationReport'
import { slaViolationCounts, slaViolationStatuses, slaViolationTimeline, type SlaViolationScope } from '@/domain/SlaViolationOverview'
import { SLA_OVERVIEW_SCOPES } from '@/presentation/config/slaViolationOverview'
import { getStatusChartColor } from '@/presentation/config/issueBadgeColors'
import { MONTHLY_COUNT_COLORS } from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'

interface Props {
  report: SlaViolationReport
  tickets: SlaViolationTicket[]
  scopedTickets: SlaViolationTicket[]
  scope: SlaViolationScope
  status: string | null
  bucket: string | null
  onScopeChange: (scope: SlaViolationScope) => void
  onStatusChange: (status: string | null) => void
  onBucketChange: (bucket: string | null) => void
}

const icons = { all: ShieldAlert, initial_response: AlarmClock, resolution: Clock3, both: Layers }

export default function SlaViolationOverview({ report, tickets, scopedTickets, scope, status, bucket, onScopeChange, onStatusChange, onBucketChange }: Props) {
  const counts = useMemo(() => slaViolationCounts(tickets), [tickets])
  const statuses = useMemo(() => slaViolationStatuses(scopedTickets), [scopedTickets])
  const timeline = useMemo(() => slaViolationTimeline(report, scopedTickets), [report, scopedTickets])
  const maximum = Math.max(1, ...timeline.buckets.map((item) => item.count))
  const total = scopedTickets.length

  return (
    <>
      <section aria-label="SLA 위반 요약" className="grid grid-cols-2 gap-3 lg:grid-cols-4 sm:gap-4">
        {SLA_OVERVIEW_SCOPES.map(({ key, label, tone, valueTone, selectionRing, hoverRing }) => {
          const Icon = icons[key]
          return (
            <button key={key} type="button" aria-label={`${label} ${counts[key].toLocaleString('ko-KR')}건 보기`} aria-pressed={scope === key}
              onClick={() => onScopeChange(scope === key ? 'all' : key)}
              className={`card flex min-w-0 flex-col gap-2 text-left transition-shadow duration-300 hover:shadow-apple-lg hover:ring-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${hoverRing} ${scope === key ? `ring-2 ${selectionRing}` : ''}`}>
              <div className="flex items-center gap-2">
                <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${tone}`}><Icon size={13} aria-hidden="true" /></span>
                <span className="break-keep text-caption font-semibold leading-none tracking-wider text-apple-light">{label}</span>
              </div>
              <p className={`text-metric font-semibold leading-none tracking-tight tabular-nums ${valueTone}`}>{counts[key].toLocaleString('ko-KR')}<span className="ml-2 text-caption font-medium text-apple-light">건</span></p>
            </button>
          )
        })}
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <section aria-label="위반 티켓의 현재 상태" className="card min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-section-title font-semibold text-apple-dark">현재 상태별 위반 티켓</h2>
            <span className="text-caption tabular-nums text-apple-mid">{total.toLocaleString('ko-KR')}건</span>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {statuses.map((item) => {
              const percentage = total > 0 ? item.count / total * 100 : 0
              return (
                <button key={item.status} type="button" aria-label={`${item.status} 위반 티켓 ${item.count.toLocaleString('ko-KR')}건 보기`} aria-pressed={status === item.status}
                  onClick={() => onStatusChange(status === item.status ? null : item.status)}
                  className={`min-w-0 rounded-xl border p-3 text-left transition-colors hover:bg-apple-gray focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${status === item.status ? 'border-brand-400 bg-brand-50' : 'border-apple-divider/60 bg-apple-gray/50'}`}>
                  <span className="flex min-w-0 items-center gap-2 text-caption font-medium text-apple-dark">
                    <span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: getStatusChartColor(item.status) }} />
                    <span className="break-words">{item.status}</span>
                  </span>
                  <div className="mt-2 flex justify-between gap-2 text-caption tabular-nums">
                    <span className="font-semibold text-apple-dark">{item.count.toLocaleString('ko-KR')}건</span><span className="text-apple-mid">{percentage.toFixed(1)}%</span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-apple-divider/60"><div className="h-full rounded-full" style={{ width: `${percentage}%`, backgroundColor: getStatusChartColor(item.status) }} /></div>
                </button>
              )
            })}
          </div>
          {statuses.length === 0 && <p className="py-12 text-center text-label text-apple-mid">조건에 맞는 위반 티켓이 없습니다.</p>}
        </section>

        <section aria-label="위반 티켓 생성 추이" className="card min-w-0">
          <h2 className="text-section-title font-semibold text-apple-dark">{report.period === 'year' ? '생성월별' : '생성일별'} 위반 티켓</h2>
          <div className="mt-5 overflow-x-auto">
            <div className="flex h-64 min-w-full items-end gap-2 border-b" style={{ borderColor: CHART_COLORS.grid, minWidth: `max(280px, calc(var(--font-size-caption) * ${timeline.buckets.length * (report.period === 'year' ? 3 : 3.5)}))` }}>
              {timeline.buckets.map((item) => (
                <button key={item.key} type="button" aria-label={`${item.key} 생성 위반 티켓 ${item.count.toLocaleString('ko-KR')}건 보기`} aria-pressed={bucket === item.key}
                  title={`${item.key} · ${item.count.toLocaleString('ko-KR')}건`} onClick={() => onBucketChange(bucket === item.key ? null : item.key)}
                  className={`flex h-full min-w-0 flex-1 flex-col items-center justify-end rounded-t-lg px-0.5 transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${bucket === item.key ? 'bg-brand-50 ring-2 ring-inset ring-brand-400' : ''}`}>
                  <span className="mb-2 text-caption font-semibold tabular-nums text-apple-dark">{item.count.toLocaleString('ko-KR')}</span>
                  <span className="w-full max-w-10 rounded-t-md" style={{ backgroundColor: MONTHLY_COUNT_COLORS.created, height: `${item.count / maximum * 68}%`, minHeight: item.count > 0 ? 3 : 0 }} />
                  <span className={`my-2 whitespace-nowrap text-caption ${bucket === item.key ? 'font-semibold' : ''}`} style={{ color: CHART_COLORS.axisText }}>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
          {timeline.unassigned > 0 && <p role="status" className="mt-3 text-caption text-amber-700">생성일 미확인·기간 밖 {timeline.unassigned.toLocaleString('ko-KR')}건</p>}
        </section>
      </div>
    </>
  )
}
