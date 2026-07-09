// frontend/src/presentation/components/cards/SummaryCard.tsx
interface Props {
  label: string
  value: number | string
  sub?: string
  color?: 'blue' | 'red' | 'green' | 'yellow' | 'gray'
  onClick?: () => void
}

const colorMap = {
  blue:   { dot: 'bg-status-data',    val: 'text-blue-600'   },
  red:    { dot: 'bg-status-pending', val: 'text-red-600'    },
  green:  { dot: 'bg-status-impl',    val: 'text-green-600'  },
  yellow: { dot: 'bg-status-review',  val: 'text-amber-600'  },
  gray:   { dot: 'bg-status-todo',    val: 'text-gray-700'   },
}

export default function SummaryCard({ label, value, sub, color = 'blue', onClick }: Props) {
  const c = colorMap[color]
  return (
    <div
      className={`card flex flex-col gap-2 hover:shadow-apple-lg transition-shadow duration-300 ${
        onClick ? 'cursor-pointer hover:ring-2 hover:ring-red-300' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${c.dot} flex-shrink-0`} />
        <p className="text-ui-xs 3xl:text-ui-sm font-semibold text-apple-light uppercase tracking-wider leading-none">
          {label}
        </p>
      </div>
      <p className={`text-ui-xl 3xl:text-ui-2xl font-semibold leading-none tracking-tight ${c.val}`}>{value}</p>
      {sub && <p className="text-ui-xs 3xl:text-ui-sm text-apple-light">{sub}</p>}
    </div>
  )
}
