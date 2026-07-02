interface Props {
  label: string
  value: number | string
  sub?: string
  color?: 'blue' | 'red' | 'green' | 'yellow' | 'gray'
  icon?: string
}

const colorMap = {
  blue:   'bg-blue-50   text-blue-700   border-blue-100',
  red:    'bg-red-50    text-red-700    border-red-100',
  green:  'bg-green-50  text-green-700  border-green-100',
  yellow: 'bg-yellow-50 text-yellow-700 border-yellow-100',
  gray:   'bg-gray-50   text-gray-700   border-gray-100'
}

export default function SummaryCard({ label, value, sub, color = 'blue', icon }: Props) {
  return (
    <div className={`card border ${colorMap[color]} flex flex-col gap-1`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
        {icon && <span className="mr-1">{icon}</span>}{label}
      </p>
      <p className="text-3xl font-bold">{value}</p>
      {sub && <p className="text-xs opacity-60">{sub}</p>}
    </div>
  )
}
