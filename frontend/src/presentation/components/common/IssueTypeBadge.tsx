// frontend/src/presentation/components/common/IssueTypeBadge.tsx
export function IssueTypeBadge({ type, className = '' }: { type: string; className?: string }) {
  return <span className={`badge-type ${className}`}>{type}</span>
}
