// frontend/src/presentation/components/common/StatusBadge.tsx
import { getStatusBadgeStyle } from '@/presentation/config/issueBadgeColors'

export function StatusBadge({ status, size = 'sm' }: { status: string; size?: 'xs' | 'sm' | 'md' }) {
  const sizeClass = size === 'xs' ? 'text-[10px]' : size === 'md' ? 'text-ui-sm' : 'text-xs'
  return <span className={`inline-block max-w-full break-words rounded-full border px-2 py-0.5 font-medium ${sizeClass}`} style={getStatusBadgeStyle(status)}>{status}</span>
}
