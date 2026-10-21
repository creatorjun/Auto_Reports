// frontend/src/presentation/components/sla-status/SlaStatusOverview.tsx
import { AlarmClock, Clock3, Layers, PauseCircle } from 'lucide-react'
import type { SlaStatusScope, SlaStatusTicket } from '@/domain/SLAStatus'
import { slaStatusCounts } from '@/application/services/slaStatus'

const scopes = [
  { key: 'all', label: '전체 대상 티켓', icon: Layers },
  { key: 'urgent', label: '잔여 10% 미만', icon: AlarmClock },
  { key: 'running', label: '진행 중 SLA 포함', icon: Clock3 },
  { key: 'paused', label: '일시정지 SLA 포함', icon: PauseCircle },
] as const

export default function SlaStatusOverview({ tickets, scope, onChange }: { tickets: SlaStatusTicket[]; scope: SlaStatusScope; onChange: (scope: SlaStatusScope) => void }) {
  const counts = slaStatusCounts(tickets)
  return (
    <section aria-label="SLA 현황 요약 필터" className="grid grid-cols-2 gap-3 lg:grid-cols-4 sm:gap-4">
      {scopes.map(({ key, label, icon: Icon }) => (
        <button key={key} type="button" aria-pressed={scope === key} aria-controls="sla-status-results"
          onClick={() => onChange(scope === key ? 'all' : key)}
          className={`card flex min-w-0 flex-col gap-2 text-left transition-shadow hover:shadow-apple-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${scope === key ? 'ring-2 ring-brand-500' : ''}`}>
          <span className="flex items-center gap-2"><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${key === 'urgent' ? 'bg-red-50 text-red-600' : 'bg-brand-50 text-brand-600'}`}><Icon size={13} aria-hidden="true" /></span><span className="text-caption font-semibold leading-none text-apple-light">{label}</span></span>
          <span className={`text-metric font-semibold leading-none tracking-tight tabular-nums ${key === 'urgent' ? 'text-red-600' : 'text-brand-600'}`}>{counts[key].toLocaleString('ko-KR')}<span className="ml-2 text-caption font-medium text-apple-light">건</span></span>
        </button>
      ))}
    </section>
  )
}
