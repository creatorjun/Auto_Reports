// frontend/src/presentation/components/common/IssueTypeIcon.tsx
import {
  AlertTriangle,
  BadgeCheck,
  HardDrive,
  Headset,
  KeyRound,
  Lightbulb,
  ShieldAlert,
  Tag,
  type LucideIcon,
} from 'lucide-react'

interface IssueTypeVisual {
  icon: LucideIcon
  label: string
  className: string
}

function getVisual(type: string): IssueTypeVisual {
  if (type.includes('승인된 서비스 요청')) {
    return { icon: BadgeCheck, label: '승인된 서비스 요청', className: 'bg-emerald-50 text-emerald-600 ring-emerald-200' }
  }
  if (type.includes('서비스 요청')) {
    return { icon: Headset, label: '서비스 요청', className: 'bg-blue-50 text-blue-600 ring-blue-200' }
  }
  if (type.includes('개선')) {
    return { icon: Lightbulb, label: '개선 요청', className: 'bg-amber-50 text-amber-600 ring-amber-200' }
  }
  if (type.includes('인시던트')) {
    return { icon: AlertTriangle, label: '인시던트', className: 'bg-red-50 text-red-600 ring-red-200' }
  }
  if (type.toUpperCase().includes('CVE')) {
    return { icon: ShieldAlert, label: 'CVE', className: 'bg-violet-50 text-violet-600 ring-violet-200' }
  }
  if (type.includes('라이선스') || type.includes('라이센스')) {
    return { icon: KeyRound, label: '라이선스 요청', className: 'bg-indigo-50 text-indigo-600 ring-indigo-200' }
  }
  if (type.includes('H/W') || type.includes('하드웨어')) {
    return { icon: HardDrive, label: 'H/W 장애 요청', className: 'bg-orange-50 text-orange-600 ring-orange-200' }
  }
  return { icon: Tag, label: type || '기타 요청', className: 'bg-gray-50 text-gray-600 ring-gray-200' }
}

export function IssueTypeIcon({ type }: { type: string }) {
  const visual = getVisual(type)
  const Icon = visual.icon
  return (
    <span
      role="img"
      aria-label={`${visual.label} 유형`}
      title={visual.label}
      className={`inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md ring-1 ring-inset ${visual.className}`}
    >
      <Icon size={13} aria-hidden="true" />
    </span>
  )
}
