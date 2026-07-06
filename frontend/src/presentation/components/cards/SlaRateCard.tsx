// frontend/src/presentation/components/cards/SlaRateCard.tsx
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

function getColorKey(rate: number): 'green' | 'yellow' | 'red' {
  if (rate >= 80) return 'green'
  if (rate >= 50) return 'yellow'
  return 'red'
}

const colorMap = {
  green:  { ring: '#22c55e', track: '#dcfce7', text: 'text-green-600',  badge: 'bg-green-50 text-green-700'  },
  yellow: { ring: '#f59e0b', track: '#fef3c7', text: 'text-amber-600',  badge: 'bg-amber-50 text-amber-700'  },
  red:    { ring: '#ef4444', track: '#fee2e2', text: 'text-red-500',    badge: 'bg-red-50 text-red-700'      },
}

export default function SlaRateCard({ label, rate, met, total, slaFields = [] }: SlaRateCardProps) {
  const c = colorMap[getColorKey(rate)]
  const r = 32
  const circ = 2 * Math.PI * r
  const dash = (rate / 100) * circ

  return (
    <div className="card flex flex-col gap-3">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-semibold text-apple-dark">{label}</p>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${c.badge}`}>
          {met}/{total}건
        </span>
      </div>

      {/* 도넛 + 요약 */}
      <div className="flex items-center gap-4">
        <div className="relative flex-shrink-0 w-[72px] h-[72px]">
          <svg width="72" height="72" viewBox="0 0 72 72" className="-rotate-90">
            <circle cx="36" cy="36" r={r} fill="none" stroke={c.track} strokeWidth="7" />
            <circle
              cx="36" cy="36" r={r} fill="none"
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
          <div className="flex justify-between text-[12px]">
            <span className="text-apple-light">준수</span>
            <span className={`font-semibold ${c.text}`}>{met}건</span>
          </div>
          <div className="w-full h-1.5 rounded-full" style={{ background: c.track }}>
            <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${rate}%`, background: c.ring }} />
          </div>
          <div className="flex justify-between text-[12px]">
            <span className="text-apple-light">위반</span>
            <span className="font-semibold text-apple-dark">{total - met}건</span>
          </div>
          <p className="text-[10px] text-apple-light/70 mt-0.5">최근 30일 · Jira SLA 기준</p>
        </div>
      </div>

      {/* SLA 필드별 세부 */}
      {slaFields.length > 0 && (
        <div className="border-t border-apple-divider pt-2 flex flex-col gap-1.5">
          {slaFields.map((f) => {
            const fc = colorMap[getColorKey(f.rate)]
            return (
              <div key={f.name} className="flex items-center gap-2">
                <span className="text-[11px] text-apple-light flex-1 truncate" title={f.name}>{f.name}</span>
                <div className="w-16 h-1 rounded-full" style={{ background: fc.track }}>
                  <div className="h-1 rounded-full" style={{ width: `${f.rate}%`, background: fc.ring }} />
                </div>
                <span className={`text-[11px] font-medium tabular-nums ${fc.text}`}>{f.rate}%</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
