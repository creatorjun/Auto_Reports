// frontend/src/presentation/components/cards/SlaRateCard.tsx
interface SlaRateCardProps {
  label: string
  rate: number       // 0~100
  met: number
  total: number
  thresholdLabel: string  // e.g. "24시간 이내" or "30일 이내"
  color?: 'green' | 'yellow' | 'red'
}

function getColor(rate: number) {
  if (rate >= 80) return 'green'
  if (rate >= 50) return 'yellow'
  return 'red'
}

const colorMap = {
  green:  { ring: '#22c55e', track: '#dcfce7', text: 'text-green-600',  bg: 'bg-green-50'  },
  yellow: { ring: '#f59e0b', track: '#fef3c7', text: 'text-amber-600',  bg: 'bg-amber-50'  },
  red:    { ring: '#ef4444', track: '#fee2e2', text: 'text-red-500',    bg: 'bg-red-50'    },
}

export default function SlaRateCard({ label, rate, met, total, thresholdLabel }: SlaRateCardProps) {
  const c = colorMap[getColor(rate)]
  const r = 36
  const circ = 2 * Math.PI * r
  const dash = (rate / 100) * circ

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold text-apple-light uppercase tracking-wider">{label}</p>
          <p className="text-[11px] text-apple-light/70 mt-0.5">{thresholdLabel} · 최근 30일</p>
        </div>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${c.bg} ${c.text}`}>
          {met}/{total}건
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* 도넛 링 */}
        <div className="relative flex-shrink-0 w-20 h-20">
          <svg width="80" height="80" viewBox="0 0 80 80" className="-rotate-90">
            {/* track */}
            <circle cx="40" cy="40" r={r} fill="none" stroke={c.track} strokeWidth="8" />
            {/* progress */}
            <circle
              cx="40" cy="40" r={r} fill="none"
              stroke={c.ring} strokeWidth="8"
              strokeDasharray={`${dash} ${circ}`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-[16px] font-bold leading-none ${c.text}`}>{rate}%</span>
          </div>
        </div>

        {/* 범례 */}
        <div className="flex flex-col gap-1.5 flex-1">
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-apple-light">준수</span>
            <span className={`text-[13px] font-semibold ${c.text}`}>{met}건</span>
          </div>
          <div className="w-full h-1.5 rounded-full" style={{ background: c.track }}>
            <div
              className="h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${rate}%`, background: c.ring }}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-apple-light">미준수</span>
            <span className="text-[13px] font-semibold text-apple-dark">{total - met}건</span>
          </div>
        </div>
      </div>
    </div>
  )
}
