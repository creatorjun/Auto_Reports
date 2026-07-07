// frontend/src/presentation/components/cards/SummaryCard.tsx
interface Props {
  label: string
  value: number | string
  sub?: string
  color?: 'blue' | 'red' | 'green' | 'yellow' | 'gray'
  onClick?: () => void
}

const colorMap = {
  blue:   { dot: 'bg-blue-500',   val: 'text-blue-600'  },
  red:    { dot: 'bg-red-500',    val: 'text-red-600'   },
  green:  { dot: 'bg-green-500',  val: 'text-green-600' },
  yellow: { dot: 'bg-amber-500',  val: 'text-amber-600' },
  gray:   { dot: 'bg-gray-400',   val: 'text-gray-700'  }
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
        <p className="text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wider leading-none">
          {label}
        </p>
        {onClick && <span className="ml-auto text-[10px] text-apple-light/60">클릭 ↗</span>}
      </div>
      <p className={`text-[32px] 3xl:text-[38px] font-semibold leading-none tracking-tight ${c.val}`}>{value}</p>
      {sub && <p className="text-[11px] 3xl:text-[12px] text-apple-light">{sub}</p>}
    </div>
  )
}
