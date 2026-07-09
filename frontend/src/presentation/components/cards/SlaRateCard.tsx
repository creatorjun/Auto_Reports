// frontend/src/presentation/components/cards/SlaRateCard.tsx
import { SLA_COLOR_MAP, SLA_TARGET_RATE, SLA_RING_RADIUS } from '@/shared/constants'

interface SlaField {
  name: string
  met: number
  breached: number
  rate: number
}

interface SlaRateCardProps {
  label: string
  rate: number
  met: number
  total: number
  slaFields?: SlaField[]
}

function getColorKey(rate: number): keyof typeof SLA_COLOR_MAP {
  if (rate >= SLA_TARGET_RATE) return 'green'
  if (rate >= 50) return 'yellow'
  return 'red'
}

export default function SlaRateCard({ label, rate, met, total, slaFields = [] }: SlaRateCardProps) {
  const c    = SLA_COLOR_MAP[getColorKey(rate)]
  const circ = 2 * Math.PI * SLA_RING_RADIUS
  const dash = (rate / 100) * circ

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-ui-sm font-semibold text-apple-dark">{label}</p>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${c.badge}`}>
          {met}/{total}건
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-shrink-0 w-[72px] h-[72px]">
          <svg width="72" height="72" viewBox="0 0 72 72" className="-rotate-90">
            <circle cx="36" cy="36" r={SLA_RING_RADIUS} fill="none" stroke={c.track} strokeWidth="7" />
            <circle
              cx="36" cy="36" r={SLA_RING_RADIUS} fill="none"
              stroke={c.ring} strokeWidth="7"
              strokeDasharray={`${dash} ${circ}`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-[15px] font-bold leading-none ${c.text}`}>{rate}%</span>
          </div>
        </div>

        <div className="flex flex-col gap-1.5 flex-1">
          <div className="flex justify-between text-ui-sm">
            <span className="text-apple-light">준수</span>
            <span className={`font-semibold ${c.text}`}>{met}건</span>
          </div>
          <div className="w-full h-1.5 rounded-full" style={{ background: c.track }}>
            <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${rate}%`, background: c.ring }} />
          </div>
          <div className="flex justify-between text-ui-sm">
            <span className="text-apple-light">위반</span>
            <span className="font-semibold text-apple-dark">{total - met}건</span>
          </div>
          <p className="text-ui-xs text-apple-light/70 mt-0.5">최근 30일 · Jira SLA 기준</p>
        </div>
      </div>

      {slaFields.length > 0 && (
        <div className="border-t border-apple-divider pt-2 flex flex-col gap-1.5">
          {slaFields.map((f) => {
            const fc = SLA_COLOR_MAP[getColorKey(f.rate)]
            return (
              <div key={f.name} className="flex items-center gap-2">
                <span className="text-ui-xs text-apple-light flex-1 truncate" title={f.name}>{f.name}</span>
                <div className="w-16 h-1 rounded-full" style={{ background: fc.track }}>
                  <div className="h-1 rounded-full" style={{ width: `${f.rate}%`, background: fc.ring }} />
                </div>
                <span className={`text-ui-xs font-medium tabular-nums ${fc.text}`}>{f.rate}%</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
