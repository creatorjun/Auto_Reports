// frontend/src/presentation/components/sla-violations/SlaStatusDurations.tsx
import type { SlaViolationTicket } from '@/domain/SlaViolationReport'
import { slaVisibleStatusDurations } from '@/application/services/slaViolationReport'
import { getStatusBadgeStyle } from '@/presentation/config/issueBadgeColors'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'

function percentageLabel(value: number): string {
  return value > 0 && value < 0.1 ? '<0.1%' : `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}%`
}

export default function SlaStatusDurations({ durations }: { durations: SlaViolationTicket['status_durations'] }) {
  const visible = slaVisibleStatusDurations(durations)
  if (visible === null) return <p className="text-caption text-apple-mid">상태 변경 이력이 불완전하여 체류 기간을 확인할 수 없습니다.</p>
  if (visible.length === 0) return <p className="text-caption text-apple-mid">표시할 체류 기간이 없습니다.</p>
  const total = visible.reduce((sum, { hours }) => sum + hours, 0)
  const segments = visible.map(({ status, hours }) => ({ status, hours, percentage: total > 0 ? hours / total * 100 : 0 }))
  return (
    <div>
      <dl className="flex flex-wrap gap-2">
        {segments.map(({ status, hours, percentage }) => (
          <div key={status} className="flex items-center gap-2 rounded-lg bg-apple-surface px-3 py-2 text-caption">
            <dt><StatusBadge status={status || '확인 불가'} size="md" /></dt>
            <dd className="text-label font-semibold tabular-nums text-apple-dark">{hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}시간 <span className="font-normal text-apple-mid">· {percentageLabel(percentage)}</span></dd>
          </div>
        ))}
      </dl>
      {total > 0 && (
        <div role="img" aria-label={`상태별 체류 비율 (닫힘 제외): ${segments.map(({ status, percentage }) => `${status || '확인 불가'} ${percentageLabel(percentage)}`).join(', ')}`}
          className="mt-3 flex h-8 w-full overflow-hidden rounded-lg bg-apple-surface">
          {segments.filter(({ hours }) => hours > 0).map(({ status, hours, percentage }) => (
            <div key={status} title={`${status || '확인 불가'} · ${hours.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}시간 · ${percentageLabel(percentage)}`}
              style={{ ...getStatusBadgeStyle(status), width: `${percentage}%` }}
              className="flex min-w-0 shrink-0 items-center justify-center overflow-hidden border-r last:border-r-0" aria-hidden="true">
              {percentage >= 8 && <span className="truncate px-1 text-caption font-semibold tabular-nums">{status || '확인 불가'} · {percentageLabel(percentage)}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
