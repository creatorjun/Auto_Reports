// frontend/src/presentation/components/cve/CveInventorySummary.tsx
import { Check } from 'lucide-react'
import type { CveInventoryRequest, CveInventorySnapshot } from '@/domain/CveInventory'
import { securitySeverityLabels } from '@/presentation/components/security/securityNewsFormatting'

export default function CveInventorySummary({ data, selected, onSelect }: {
  data: CveInventorySnapshot | undefined; selected: CveInventoryRequest['severity']; onSelect: (severity: CveInventoryRequest['severity']) => void
}) {
  const counts = data?.severity_counts
  const metrics = [
    { severity: 'all' as const, label: '패키지별 CVE', count: counts ? Object.values(counts).reduce((sum, value) => sum + value, 0) : null },
    ...(['critical', 'high', 'medium', 'low', 'unknown'] as const).map((severity) => ({ severity, label: securitySeverityLabels[severity], count: counts?.[severity] ?? null })),
  ]
  const colors = { all: 'text-brand-600', critical: 'text-red-600', high: 'text-amber-700', medium: 'text-apple-dark', low: 'text-green-700', unknown: 'text-apple-mid' }
  return <div role="group" aria-label="CVE 위험도 필터" className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
    {metrics.map((metric) => <button key={metric.severity} type="button" onClick={() => onSelect(metric.severity)} aria-pressed={selected === metric.severity} aria-controls="cve-inventory-results" className={`min-w-0 rounded-2xl border px-4 py-4 text-left shadow-apple-sm transition-colors focus-visible:outline-brand-500 ${selected === metric.severity ? 'border-brand-500 bg-brand-50' : 'border-apple-divider/70 bg-apple-surface hover:border-brand-400'}`}>
      <span className="flex items-center justify-between gap-2 text-caption font-medium text-apple-mid">{metric.label}{selected === metric.severity && <Check size={15} aria-hidden="true" className="text-brand-600" />}</span>
      <span className={`mt-2 block text-page-title font-semibold tabular-nums ${colors[metric.severity]}`}>{metric.count === null ? '—' : metric.count.toLocaleString('ko-KR')}</span>
    </button>)}
  </div>
}
