// frontend/src/presentation/components/sla-status/SlaStatusOverview.tsx
import { AlarmClock, Clock3, Layers, PauseCircle } from 'lucide-react'
import type { SlaStatusScope, SlaStatusTicket } from '@/domain/SLAStatus'
import { slaStatusCounts } from '@/application/services/slaStatus'

const scopes = [
  { key: 'all', label: '전체 대상 티켓', detail: '조건에 해당하는 고유 티켓', icon: Layers },
  { key: 'urgent', label: '잔여 10% 미만', detail: '임박한 SLA가 있는 티켓', icon: AlarmClock },
  { key: 'running', label: '진행 중 SLA 포함', detail: '진행 중인 대상 SLA가 있는 티켓', icon: Clock3 },
  { key: 'paused', label: '일시정지 SLA 포함', detail: '일시정지된 대상 SLA가 있는 티켓', icon: PauseCircle },
] as const

export default function SlaStatusOverview({ tickets, scope, onChange }: { tickets: SlaStatusTicket[]; scope: SlaStatusScope; onChange: (scope: SlaStatusScope) => void }) {
  const counts = slaStatusCounts(tickets)
  return (
    <section aria-label="SLA 현황 요약 필터" className="grid grid-cols-2 gap-3 lg:grid-cols-4 sm:gap-4">
      {scopes.map(({ key, label, detail, icon: Icon }) => (
        <button key={key} type="button" aria-pressed={scope === key} aria-controls="sla-status-results"
          onClick={() => onChange(scope === key ? 'all' : key)}
          className={`card flex min-w-0 flex-col gap-2 text-left transition-shadow hover:shadow-apple-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${scope === key ? 'ring-2 ring-brand-500' : ''}`}>
          <span className="flex items-center gap-2 text-caption font-semibold text-apple-mid"><Icon size={16} className={key === 'urgent' ? 'shrink-0 text-red-600' : 'shrink-0 text-brand-600'} aria-hidden="true" />{label}</span>
          <span className={`text-metric font-semibold tabular-nums ${key === 'urgent' ? 'text-red-600' : 'text-apple-dark'}`}>{counts[key].toLocaleString('ko-KR')}<span className="ml-1.5 text-caption font-medium text-apple-mid">건</span></span>
          <span className="text-caption text-apple-mid">{detail}</span>
        </button>
      ))}
    </section>
  )
}
