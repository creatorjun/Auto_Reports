// frontend/src/presentation/components/cards/WorkTypeSummaryCard.tsx
import { CircleDot } from 'lucide-react'

interface Props {
  label: string
  count: number
  onClick: () => void
  tone?: 'blue' | 'green' | 'red' | 'yellow' | 'purple'
}

const toneMap = {
  blue:   { edge: 'border-t-blue-400',   bg: 'bg-blue-50',   text: 'text-blue-600',   ring: 'focus-visible:ring-blue-400' },
  green:  { edge: 'border-t-green-400',  bg: 'bg-green-50',  text: 'text-green-600',  ring: 'focus-visible:ring-green-400' },
  red:    { edge: 'border-t-red-400',    bg: 'bg-red-50',    text: 'text-red-600',    ring: 'focus-visible:ring-red-400' },
  yellow: { edge: 'border-t-amber-400',  bg: 'bg-amber-50',  text: 'text-amber-600',  ring: 'focus-visible:ring-amber-400' },
  purple: { edge: 'border-t-purple-700', bg: 'bg-purple-100', text: 'text-purple-700', ring: 'focus-visible:ring-purple-700' },
} as const

export default function WorkTypeSummaryCard({
  label,
  count,
  onClick,
  tone = 'blue',
}: Props) {
  const colors = toneMap[tone]
  return (
    <button
      type="button"
      data-pdf-metric=""
      data-pdf-label={label}
      data-pdf-value={count.toString()}
      className={`card min-w-0 flex items-center justify-between gap-4 border-t-2 text-left hover:shadow-apple-lg transition-all duration-300 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 ${colors.edge} ${colors.ring}`}
      aria-label={`${label} 현재 열린 요청 ${count}건 보기`}
      onClick={onClick}
    >
      <span className="min-w-0">
        <span className="block truncate text-ui-xs 3xl:text-ui-sm font-semibold text-apple-light uppercase tracking-wider">
          {label}
        </span>
        <span className={`mt-2 flex items-center gap-1.5 text-ui-xs 3xl:text-ui-sm font-medium ${colors.text}`}>
          <span className={`flex h-5 w-5 items-center justify-center rounded-full ${colors.bg}`}><CircleDot size={12} className="shrink-0" /></span>
          현재 열림
        </span>
      </span>
      <span className={`shrink-0 text-ui-2xl 3xl:text-3xl font-semibold leading-none tracking-tight tabular-nums ${colors.text}`}>
        {count}
      </span>
    </button>
  )
}
