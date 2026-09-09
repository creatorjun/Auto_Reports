// frontend/src/presentation/components/annual/AnnualSummaryMetrics.tsx
import { ArrowUpRight } from 'lucide-react'

interface Metric {
  label: string
  value: number
  onClick: () => void
}

interface Props {
  period: string
  created: number
  resolved: number
  createdDetails: number
  resolvedDetails: number
  onCreated: () => void
  onResolved: () => void
  statuses: Metric[]
}

export default function AnnualSummaryMetrics({ period, created, resolved, createdDetails, resolvedDetails, onCreated, onResolved, statuses }: Props) {
  return (
    <section data-pdf-section="주요 지표" data-pdf-kind="metrics" className="space-y-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold text-apple-dark">선택 기간 실적</h2>
        <p className="text-sm text-apple-mid">{period} · 선택한 요청 유형 기준</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[
          { label: '생성 이슈', value: created, detailLabel: '기간 내 생성 상세', details: createdDetails, onClick: onCreated, color: 'rgb(var(--color-chart-muted-steel))' },
          { label: '해결 이슈', value: resolved, detailLabel: '기간 내 완료 상세', details: resolvedDetails, onClick: onResolved, color: 'rgb(var(--color-chart-muted-sage))' },
        ].map((metric) => (
          <div key={metric.label} className="overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface">
            <div data-pdf-metric="" data-pdf-label={`${period} ${metric.label}`} data-pdf-value={`${metric.value.toLocaleString('ko-KR')}건`} className="border-t-4 p-5" style={{ borderTopColor: metric.color }}>
              <p className="text-sm font-semibold text-apple-dark">{metric.label}</p>
              <p className="mt-3 text-4xl font-semibold tabular-nums tracking-tight text-apple-dark md:text-5xl">{metric.value.toLocaleString('ko-KR')}<span className="ml-2 text-base font-medium text-apple-mid">건</span></p>
            </div>
            <button type="button" onClick={metric.onClick} data-pdf-metric="" data-pdf-label={metric.detailLabel} data-pdf-value={`${metric.details.toLocaleString('ko-KR')}건`} className="flex w-full items-center justify-between gap-2 border-t border-apple-divider bg-apple-gray/50 px-5 py-3 text-left text-sm text-apple-dark transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500">
              <span>{metric.detailLabel} <strong className="ml-1 tabular-nums">{metric.details.toLocaleString('ko-KR')}건</strong></span><ArrowUpRight size={16} />
            </button>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-apple-divider bg-apple-surface p-4 md:p-5">
        <h3 className="text-sm font-semibold text-apple-dark">진행 상태별 현황</h3>
        <div className="mt-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
          {statuses.map((metric) => (
            <button key={metric.label} type="button" onClick={metric.onClick} data-pdf-metric="" data-pdf-label={metric.label} data-pdf-value={`${metric.value.toLocaleString('ko-KR')}건`} className="group flex min-w-0 flex-col items-start gap-2 rounded-xl bg-apple-gray/60 p-4 text-left transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
              <span className="text-[13px] font-medium text-apple-dark">{metric.label}</span>
              <span className="flex w-full items-center justify-between gap-2"><strong className="text-2xl font-semibold tabular-nums text-apple-dark">{metric.value.toLocaleString('ko-KR')}<span className="ml-1 text-xs font-normal text-apple-mid">건</span></strong><ArrowUpRight size={15} className="text-apple-mid group-hover:text-brand-600" /></span>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
