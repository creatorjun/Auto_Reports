// frontend/src/presentation/components/cards/WorkTypeSummaryCard.tsx
import { CircleDot } from 'lucide-react'

interface Props {
  label: string
  count: number
  onClick: () => void
}

export default function WorkTypeSummaryCard({
  label,
  count,
  onClick,
}: Props) {
  return (
    <button
      type="button"
      className="card min-w-0 flex items-center justify-between gap-4 text-left hover:shadow-apple-lg transition-all duration-300 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
      aria-label={`${label} 현재 열린 요청 ${count}건 보기`}
      onClick={onClick}
    >
      <span className="min-w-0">
        <span className="block truncate text-ui-xs 3xl:text-ui-sm font-semibold text-apple-light uppercase tracking-wider">
          {label}
        </span>
        <span className="mt-2 flex items-center gap-1.5 text-ui-xs 3xl:text-ui-sm font-medium text-blue-600">
          <CircleDot size={13} className="shrink-0" />
          현재 열림
        </span>
      </span>
      <span className="shrink-0 text-ui-2xl 3xl:text-3xl font-semibold leading-none tracking-tight text-blue-600 tabular-nums">
        {count}
      </span>
    </button>
  )
}
