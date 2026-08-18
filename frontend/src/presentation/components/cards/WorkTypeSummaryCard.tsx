// frontend/src/presentation/components/cards/WorkTypeSummaryCard.tsx
import { CheckCircle2, FilePlus } from 'lucide-react'

interface Props {
  label: string
  created: number
  resolved: number
  onCreatedClick: () => void
  onResolvedClick: () => void
}

export default function WorkTypeSummaryCard({
  label,
  created,
  resolved,
  onCreatedClick,
  onResolvedClick,
}: Props) {
  return (
    <div className="card min-w-0 flex flex-col gap-3 hover:shadow-apple-lg transition-shadow duration-300">
      <h3 className="truncate text-ui-xs 3xl:text-ui-sm font-semibold text-apple-light uppercase tracking-wider">
        {label}
      </h3>
      <div className="grid grid-cols-2 gap-2 3xl:gap-3">
        <button
          type="button"
          className="min-w-0 rounded-xl border border-blue-100 bg-blue-50/70 p-3 text-left transition-colors hover:border-blue-300 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          aria-label={`${label} 생성 이슈 ${created}건 보기`}
          onClick={onCreatedClick}
        >
          <span className="flex items-center gap-1.5 text-ui-xs 3xl:text-ui-sm font-semibold text-blue-600">
            <FilePlus size={14} className="shrink-0" />
            생성
          </span>
          <span className="mt-2 block truncate text-ui-xl 3xl:text-ui-2xl font-semibold leading-none tracking-tight text-blue-600 tabular-nums">
            {created}
          </span>
        </button>
        <button
          type="button"
          className="min-w-0 rounded-xl border border-green-100 bg-green-50/70 p-3 text-left transition-colors hover:border-green-300 hover:bg-green-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-400"
          aria-label={`${label} 완료 이슈 ${resolved}건 보기`}
          onClick={onResolvedClick}
        >
          <span className="flex items-center gap-1.5 text-ui-xs 3xl:text-ui-sm font-semibold text-green-600">
            <CheckCircle2 size={14} className="shrink-0" />
            완료
          </span>
          <span className="mt-2 block truncate text-ui-xl 3xl:text-ui-2xl font-semibold leading-none tracking-tight text-green-600 tabular-nums">
            {resolved}
          </span>
        </button>
      </div>
    </div>
  )
}
