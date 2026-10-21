// frontend/src/presentation/components/cards/AiSummaryCard.tsx
import type { AiAnalysis } from '@/domain/Report'

const sentimentConfig = {
  good:     { bg: 'bg-green-50',  border: 'border-green-200/60',  badge: 'badge-good',     label: '양호', dot: 'bg-status-impl'    },
  warning:  { bg: 'bg-amber-50',  border: 'border-amber-200/60',  badge: 'badge-warning',  label: '주의', dot: 'bg-status-review'  },
  critical: { bg: 'bg-red-50',    border: 'border-red-200/60',    badge: 'badge-critical', label: '경고', dot: 'bg-status-pending' },
}

export default function AiSummaryCard({ ai }: { ai: AiAnalysis }) {
  const cfg = sentimentConfig[ai.sentiment] ?? sentimentConfig.warning
  const bottlenecks = ai.bottlenecks ?? []
  const analyzedAt = ai.analyzed_at ? new Date(ai.analyzed_at) : null
  const analysisTime = analyzedAt && Number.isFinite(analyzedAt.getTime())
    ? analyzedAt.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
    : null
  const sections = [
    { title: '문제점', items: ai.risks, color: 'text-red-600', marker: 'text-red-400' },
    ...(bottlenecks.length ? [{ title: '병목', items: bottlenecks, color: 'text-amber-700', marker: 'text-amber-500' }] : []),
    { title: '개선 제안', items: ai.recommendations, color: 'text-brand-600', marker: 'text-brand-400' },
  ]
  return (
    <div data-pdf-kind="text" className={`rounded-2xl border ${cfg.border} ${cfg.bg} p-4 md:p-6 shadow-apple-sm`}>
      <div className="flex flex-wrap items-center gap-2.5 mb-3 md:mb-4">
        <span className={`w-2 h-2 rounded-full ${cfg.dot} flex-shrink-0`} />
        <h3 className="text-section-title font-semibold text-apple-dark">AI 종합 분석</h3>
        <span data-pdf-paragraph data-pdf-prefix="상태: " className={cfg.badge}>{cfg.label}</span>
      </div>
      {(ai.provider === 'rovo_automation' || analysisTime) && <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-apple-mid">
        {ai.provider === 'rovo_automation' && <span data-pdf-paragraph data-pdf-prefix="분석: ">Rovo</span>}
        {analysisTime && <time dateTime={ai.analyzed_at ?? undefined} data-pdf-paragraph data-pdf-prefix="분석 시각: ">{analysisTime} (KST)</time>}
      </div>}
      {ai.is_stale && <p role="status" className="mb-4 text-caption text-amber-700">보고서 데이터가 갱신되었습니다. 이 총평은 이전 분석 시점 기준입니다.</p>}
      <p className="mb-2 text-caption font-semibold text-apple-dark">요약</p>
      <p className="text-label text-apple-dark/80 leading-relaxed mb-4 md:mb-5">{ai.summary}</p>
      <div className={`grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6 ${bottlenecks.length ? 'lg:grid-cols-3' : ''}`}>
        {sections.map((section) => (
          <div key={section.title}>
            <p className={`text-caption font-semibold ${section.color} mb-2`}>{section.title}</p>
            <ul className="space-y-1.5">
              {section.items.map((item, index) => (
                <li key={index} className="text-label text-apple-dark/70 flex gap-2">
                  <span className={`${section.marker} flex-shrink-0`}>—</span>{item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
