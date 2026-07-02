import type { AiAnalysis } from '@/domain/Report'

const sentimentConfig = {
  good:     { icon: '✅', bg: 'bg-green-50',  border: 'border-green-200', badge: 'badge-good',    label: '양호' },
  warning:  { icon: '⚠️', bg: 'bg-yellow-50', border: 'border-yellow-200', badge: 'badge-warning', label: '주의' },
  critical: { icon: '🚨', bg: 'bg-red-50',    border: 'border-red-200',    badge: 'badge-critical',label: '경고' }
}

export default function AiSummaryCard({ ai }: { ai: AiAnalysis }) {
  const cfg = sentimentConfig[ai.sentiment] ?? sentimentConfig.warning
  return (
    <div className={`card border ${cfg.border} ${cfg.bg}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{cfg.icon}</span>
        <h3 className="font-bold text-gray-800">AI 종합 분석</h3>
        <span className={cfg.badge}>{cfg.label}</span>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed mb-4">{ai.summary}</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-semibold text-red-600 mb-2">🚨 주목 리스크</p>
          <ul className="space-y-1">
            {ai.risks.map((r, i) => <li key={i} className="text-xs text-gray-600">• {r}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold text-blue-600 mb-2">💡 다음 주 권고사항</p>
          <ul className="space-y-1">
            {ai.recommendations.map((r, i) => <li key={i} className="text-xs text-gray-600">• {r}</li>)}
          </ul>
        </div>
      </div>
    </div>
  )
}
