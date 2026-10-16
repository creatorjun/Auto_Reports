// frontend/src/presentation/components/sla-violations/SlaStatusDurations.tsx
import type { SlaViolationTicket } from '@/domain/SlaViolationReport'
import { slaVisibleStatusDurations } from '@/application/services/slaViolationReport'
import { getStatusChartColor } from '@/presentation/config/issueBadgeColors'

function percentageLabel(value: number): string {
  return value > 0 && value < 0.1 ? '<0.1%' : `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}%`
}

export default function SlaStatusDurations({ durations, basis }: { durations: SlaViolationTicket['status_durations']; basis: SlaViolationTicket['status_durations_basis'] }) {
  if (basis !== 'resolution_sla') return <p className="text-caption text-apple-mid">이전 보고서입니다. 다시 생성하면 SLA 기준 시간이 표시됩니다.</p>
  const visible = slaVisibleStatusDurations(durations)
  if (visible === null) return <p className="text-caption text-apple-mid">상태별 SLA 시간을 확인할 수 없습니다.</p>
  if (visible.length === 0) return <p className="text-caption text-apple-mid">표시할 상태별 SLA 시간이 없습니다.</p>
  const total = visible.reduce((sum, { hours }) => sum + hours, 0)
  const segments = visible.map(({ status, hours }) => ({ status, hours, percentage: total > 0 ? hours / total * 100 : 0 }))
  return (
    <div>
      <p className="mb-3 text-caption font-semibold tracking-wide text-apple-light">해결시간 SLA 기준</p>
      <dl className="flex flex-wrap gap-2">
        {segments.map(({ status, hours, percentage }) => (
          <div key={status} className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-apple-divider/60 bg-apple-surface px-3 py-2 text-caption">
            <dt className="flex min-w-0 items-center gap-2 text-label font-medium text-apple-dark"><span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: getStatusChartColor(status) }} />{status || '확인 불가'}</dt>
            <dd className="text-label font-semibold tabular-nums text-apple-dark">{hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}시간 <span className="font-normal text-apple-mid">· {percentageLabel(percentage)}</span></dd>
          </div>
        ))}
      </dl>
      {total > 0 && (
        <div role="img" aria-label={`상태별 SLA 사용 비율: ${segments.map(({ status, percentage }) => `${status || '확인 불가'} ${percentageLabel(percentage)}`).join(', ')}`}
          className="mt-3 flex h-10 w-full overflow-hidden rounded-lg bg-apple-surface">
          {segments.filter(({ hours }) => hours > 0).map(({ status, hours, percentage }) => (
            <div key={status} title={`${status || '확인 불가'} · ${hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}시간 · ${percentageLabel(percentage)}`}
              style={{ backgroundColor: getStatusChartColor(status), width: `${percentage}%` }}
              className="flex min-w-0 shrink-0 items-center justify-center overflow-hidden border-r border-apple-surface text-apple-dark last:border-r-0" aria-hidden="true">
              {percentage >= 8 && <span className="mx-1 truncate rounded-md bg-apple-surface px-1.5 py-0.5 text-caption font-medium tabular-nums">{status || '확인 불가'} · {percentageLabel(percentage)}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
