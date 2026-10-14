// frontend/src/presentation/components/common/SectionTitle.tsx
import type { LucideIcon } from 'lucide-react'

interface SectionTitleProps {
  icon: LucideIcon
  title: string
  subtitle?: string
}

export default function SectionTitle({ icon: Icon, title, subtitle }: SectionTitleProps) {
  return (
    <div className="flex items-center gap-2 px-1 mb-1">
      <Icon size={15} className="text-brand-500 flex-shrink-0" />
      <span className="text-section-label text-apple-dark">{title}</span>
      {subtitle && <span className="text-caption text-apple-light">{subtitle}</span>}
    </div>
  )
}
