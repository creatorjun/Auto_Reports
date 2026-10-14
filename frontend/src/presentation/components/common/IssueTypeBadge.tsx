// frontend/src/presentation/components/common/IssueTypeBadge.tsx
import { getIssueTypeBadgeStyle } from '@/presentation/config/issueBadgeColors'

export function IssueTypeBadge({ type, className = '' }: { type: string; className?: string }) {
  return <span className={`badge-type ${className}`} style={getIssueTypeBadgeStyle(type)}>{type}</span>
}
