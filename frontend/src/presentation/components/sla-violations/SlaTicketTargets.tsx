// frontend/src/presentation/components/sla-violations/SlaTicketTargets.tsx
import type { SlaViolationCycle, SlaViolationMetric, SlaViolationTicket } from '@/domain/SlaViolationReport'
import { StatusBadge } from '@/presentation/components/common/StatusBadge'
import { slaDuration, slaTimestamp } from '@/presentation/utils/slaViolationFormatters'

const METRICS: { metric: SlaViolationMetric; label: string }[] = [
  { metric: 'initial_response', label: '최초응답 SLA' },
  { metric: 'resolution', label: '해결시간 SLA' },
]

function CycleTiming({ cycle, index, repeated }: { cycle: SlaViolationCycle; index: number; repeated: boolean }) {
  const phase = cycle.ongoing ? cycle.paused ? '일시정지' : '진행 중' : '종료'
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center gap-2 text-caption">
      {repeated && <span className="font-medium text-apple-dark">{index + 1}회차</span>}
      <span className={`rounded-full px-2.5 py-1 font-medium ${cycle.breached ? 'bg-red-50 text-red-700' : cycle.ongoing ? 'bg-brand-50 text-brand-700' : 'bg-green-50 text-green-700'}`}>
        {cycle.breached ? '위반' : cycle.ongoing ? '미위반' : '준수'}
      </span>
      <span className="text-apple-mid">{phase}</span>
    </div>
    <dl className="grid min-w-0 grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
      {[
        { label: '설정 시간', value: cycle.goal_ms },
        { label: 'SLA 사용 시간', value: cycle.elapsed_ms },
        { label: '초과 시간', value: cycle.exceeded_ms },
      ].map(({ label, value }, index) => <div key={label} className={`min-w-0 ${index === 2 ? 'col-span-2 sm:col-span-1' : ''}`}>
        <dt className="text-caption text-apple-light">{label}</dt>
        <dd className={`mt-1 break-keep break-words text-metric font-semibold tracking-tight tabular-nums ${index === 2 && cycle.breached ? 'text-red-600' : 'text-apple-dark'}`}>{slaDuration(value)}</dd>
      </div>)}
    </dl>
    {cycle.breached && <dl className="flex flex-wrap items-start gap-x-5 gap-y-2 border-t border-apple-divider/60 pt-3">
      <div><dt className="mb-1 text-caption text-apple-mid">위반 당시 상태</dt><dd><StatusBadge status={cycle.status || '확인 불가'} size="md" /></dd></div>
      <div><dt className="mb-1 text-caption text-apple-mid">위반 시각</dt><dd className="break-words text-label text-apple-dark">{slaTimestamp(cycle.breached_at)}{cycle.breached_at ? ' KST' : ''}</dd></div>
    </dl>}
    {repeated && <p className="break-words text-caption text-apple-mid">{slaTimestamp(cycle.started_at)} – {cycle.ongoing ? '진행 중' : slaTimestamp(cycle.stopped_at)}</p>}
  </div>
}

export default function SlaTicketTargets({ ticket }: { ticket: SlaViolationTicket }) {
  const legacy = ticket.sla_cycles == null
  const violated = METRICS.filter(({ metric }) => ticket.breaches.some((breach) => breach.metric === metric))
  return <section aria-label="SLA 목표 및 위반 현황" className="mb-5 space-y-3">
    <dl><dt className="text-caption text-apple-light">위반 항목</dt><dd className="mt-1 break-words text-label font-semibold text-apple-dark">{violated.map(({ label }) => label).join(' · ') || '없음'}</dd></dl>
    <div className="grid min-w-0 gap-3 xl:grid-cols-2">
      {METRICS.map(({ metric, label }) => {
        const cycles = ticket.sla_cycles?.filter((cycle) => cycle.metric === metric) ?? []
        return <section key={metric} aria-label={`${label} 시간 상세`} className="min-w-0 rounded-xl border border-apple-divider/60 bg-apple-surface p-4 shadow-apple-sm">
          <h3 className="mb-3 text-section-title font-semibold text-apple-dark">{label}</h3>
          {cycles.length > 0 ? <div className="space-y-4 divide-y divide-apple-divider">{cycles.map((cycle, index) => <div key={`${cycle.started_at}:${index}`} className={index ? 'pt-4' : ''}><CycleTiming cycle={cycle} index={index} repeated={cycles.length > 1} /></div>)}</div> : <p className="text-label text-apple-mid">{legacy ? '설정 시간 · 사용 시간 · 초과 시간 확인 불가' : 'SLA 측정 내역 없음'}</p>}
        </section>
      })}
    </div>
    {legacy && <p role="status" className="text-caption text-amber-700">이 보고서에는 SLA 시간이 저장되어 있지 않습니다. 보고서를 다시 생성하면 확인할 수 있습니다.</p>}
  </section>
}
