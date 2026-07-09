// frontend/src/presentation/components/cards/AiSummaryCard.tsx
import type { AiAnalysis } from '@/domain/Report'

const sentimentConfig = {
  good:     { bg: 'bg-green-50',  border: 'border-green-200/60',  badge: 'badge-good',     label: '양호', dot: 'bg-status-impl'    },
  warning:  { bg: 'bg-amber-50',  border: 'border-amber-200/60',  badge: 'badge-warning',  label: '주의', dot: 'bg-status-review'  },
  critical: { bg: 'bg-red-50',    border: 'border-red-200/60',    badge: 'badge-critical', label: '경고', dot: 'bg-status-pending' },
}

export default function AiSummaryCard({ ai }: { ai: AiAnalysis }) {
  const cfg = sentimentConfig[ai.sentiment] ?? sentimentConfig.warning
  return (
    <div className={`rounded-2xl border ${cfg.border} ${cfg.bg} p-4 md:p-6 shadow-apple-sm`}>
      <div className="flex items-center gap-2.5 mb-3 md:mb-4">
        <span className={`w-2 h-2 rounded-full ${cfg.dot} flex-shrink-0`} />
        <h3 className="text-ui-md md:text-ui-lg font-semibold text-apple-dark">AI 종합 분석</h3>
        <span className={cfg.badge}>{cfg.label}</span>
      </div>
      <p className="text-ui-sm md:text-ui-base text-apple-dark/80 leading-relaxed mb-4 md:mb-5">{ai.summary}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6">
        <div>
          <p className="text-ui-xs font-semibold text-red-600 uppercase tracking-wider mb-2">주목 리스크</p>
          <ul className="space-y-1.5">
            {ai.risks.map((r, i) => (
              <li key={i} className="text-ui-sm text-apple-dark/70 flex gap-2">
                <span className="text-red-400 flex-shrink-0">—</span>{r}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-ui-xs font-semibold text-brand-600 uppercase tracking-wider mb-2">다음 주 권고사항</p>
          <ul className="space-y-1.5">
            {ai.recommendations.map((r, i) => (
              <li key={i} className="text-ui-sm text-apple-dark/70 flex gap-2">
                <span className="text-brand-400 flex-shrink-0">—</span>{r}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
