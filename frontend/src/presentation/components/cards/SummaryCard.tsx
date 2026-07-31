// frontend/src/presentation/components/cards/SummaryCard.tsx
import type { LucideIcon } from 'lucide-react'
import {
  CalendarPlus, CalendarCheck, FilePlus, CheckCircle2,
  Eye, FolderSearch, Clock, AlertTriangle
} from 'lucide-react'

interface Props {
  label: string
  value: number | string
  sub?: string
  color?: 'blue' | 'red' | 'green' | 'yellow' | 'gray'
  icon?: LucideIcon
  onClick?: () => void
}

const colorMap = {
  blue:   { icon: 'text-blue-500',   val: 'text-blue-600',  bg: 'bg-blue-50'   },
  red:    { icon: 'text-red-500',    val: 'text-red-600',   bg: 'bg-red-50'    },
  green:  { icon: 'text-green-500',  val: 'text-green-600', bg: 'bg-green-50'  },
  yellow: { icon: 'text-amber-500',  val: 'text-amber-600', bg: 'bg-amber-50'  },
  gray:   { icon: 'text-gray-400',   val: 'text-gray-700',  bg: 'bg-gray-50'   },
}

export const SUMMARY_ICONS = {
  yearCreated:    CalendarPlus,
  yearResolved:   CalendarCheck,
  weekCreated:    FilePlus,
  weekResolved:   CheckCircle2,
  issueReview:    Eye,
  dataRequest:    FolderSearch,
  resultPending:  Clock,
  incomplete:     AlertTriangle,
} as const

export default function SummaryCard({ label, value, sub, color = 'blue', icon: Icon, onClick }: Props) {
  const c = colorMap[color]
  return (
    <div
      className={`card flex flex-col gap-2 hover:shadow-apple-lg transition-shadow duration-300 ${
        onClick ? 'cursor-pointer hover:ring-2 hover:ring-red-300' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2">
        {Icon && (
          <span className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${c.bg}`}>
            <Icon size={13} className={c.icon} />
          </span>
        )}
        <p className="text-ui-xs 3xl:text-ui-sm font-semibold text-apple-light uppercase tracking-wider leading-none">
          {label}
        </p>
      </div>
      <p className={`text-ui-xl 3xl:text-ui-2xl font-semibold leading-none tracking-tight ${c.val}`}>{value}</p>
      {sub && <p className="text-ui-xs 3xl:text-ui-sm text-apple-light">{sub}</p>}
    </div>
  )
}
